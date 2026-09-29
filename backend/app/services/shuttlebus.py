"""摆渡车业务规则：发车判定、趟次状态流转、航站楼标准与车辆下限校验都收在这里。

发车规则（调度员约定）：
- 按趟次的上车人数与旅客等待时长判断能不能发车；
- 旅客等待数据缺失的趟次先挂「待确认」，不许直接放行；
- 等待超过航站楼约定阈值的趟次挂「超时待处置」，必须先处置再发车；
- 确认发车时上车人数仍要达到该航站楼的最小发车人数；
- 可用摆渡车少于当天需求下限时不许排新趟次，并说明差几辆；
- 同一辆摆渡车重复登记同一趟次时按时间去重，只留最近一条记录。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.store import store

MODULE = "shuttlebus"
REQUIRED_FIELDS = ["趟次编号", "航站楼", "摆渡车编号", "上车人数"]
STATUS_ORDER = ["待确认", "待发车", "超时待处置", "已发车", "已取消"]
CLOSED_STATUSES = ["已发车", "已取消"]
STANDARD_FIELDS = ["最小发车人数", "等待阈值分钟", "当天需求下限", "可用摆渡车"]

# 各航站楼的发车标准分开设置，互不套用。
TERMINAL_STANDARDS: dict[str, dict[str, int]] = {
    "T1": {"最小发车人数": 20, "等待阈值分钟": 15, "当天需求下限": 4, "可用摆渡车": 5},
    "T2": {"最小发车人数": 25, "等待阈值分钟": 20, "当天需求下限": 3, "可用摆渡车": 3},
    "T3": {"最小发车人数": 15, "等待阈值分钟": 10, "当天需求下限": 2, "可用摆渡车": 1},
}


def _to_int(value: Any) -> int | None:
    """把输入解析成整数；空值或无法解析时返回 None，由调用方决定怎么处理。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ShuttlebusService:
    # ---------- 列表与筛选 ----------

    def _filtered(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        terminal: str | None = None,
        service_date: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("趟次编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if terminal:
            rows = [row for row in rows if row.get("航站楼") == terminal]
        if service_date:
            rows = [row for row in rows if row.get("服务日期") == service_date]
        return rows

    def _passenger_total(self, rows: list[dict[str, Any]]) -> int:
        return sum(_to_int(row.get("上车人数")) or 0 for row in rows)

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        terminal: str | None = None,
        service_date: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, int]]:
        """分页返回趟次，同时给出整批（非单页）的人数合计与状态计数。

        页面上的「本批上车人数合计」和导出清单里的合计都取自这里，
        保证同一批趟次两边对得上。
        """
        rows = self._filtered(keyword=keyword, status=status, terminal=terminal, service_date=service_date)
        total = len(rows)
        passenger_total = self._passenger_total(rows)
        status_counts = {name: sum(1 for row in rows if row.get("status") == name) for name in STATUS_ORDER}
        start = max(page - 1, 0) * size
        return rows[start:start + size], total, passenger_total, status_counts

    def export_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        terminal: str | None = None,
        service_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, int]:
        """导出发车清单：与列表共用同一套筛选口径，人数合计自然对得上。"""
        rows = self._filtered(keyword=keyword, status=status, terminal=terminal, service_date=service_date)
        return rows, len(rows), self._passenger_total(rows)

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    # ---------- 趟次登记 ----------

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"
        terminal = str(values["航站楼"]).strip().upper()
        standard = TERMINAL_STANDARDS.get(terminal)
        if standard is None:
            return None, f"航站楼 {terminal} 未配置发车标准，请先在标准设置里补齐"
        boarding = _to_int(values.get("上车人数"))
        if boarding is None or boarding < 0:
            return None, "上车人数需为非负整数"
        service_date = str(values.get("服务日期") or "").strip() or date.today().isoformat()
        try:
            date.fromisoformat(service_date)
        except ValueError:
            return None, "服务日期格式应为 YYYY-MM-DD"

        available = standard["可用摆渡车"]
        floor = standard["当天需求下限"]
        if available < floor:
            shortage = floor - available
            return None, (
                f"{terminal} 可用摆渡车 {available} 辆，低于当天需求下限 {floor} 辆，"
                f"还差 {shortage} 辆，不许排新趟次"
            )

        # 同一辆摆渡车重复登记同一趟次：按时间去重，只留最近一条（即本次登记）。
        rows = store.rows(MODULE)
        trip_no = str(values["趟次编号"]).strip()
        bus_no = str(values["摆渡车编号"]).strip()
        kept = [
            row for row in rows
            if not (str(row.get("趟次编号")) == trip_no and str(row.get("摆渡车编号")) == bus_no)
        ]
        deduped = len(rows) - len(kept)
        if deduped:
            rows[:] = kept

        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["趟次编号"] = trip_no
        entry["航站楼"] = terminal
        entry["摆渡车编号"] = bus_no
        entry["上车人数"] = boarding
        entry["旅客等待时长"] = _to_int(values.get("旅客等待时长"))
        entry["服务日期"] = service_date
        entry["登记时间"] = _now()
        entry["status"] = self._evaluate(entry, standard)
        self._sync_flags(entry)
        rows.append(entry)

        message = f"摆渡趟次已登记，当前状态：{entry['status']}"
        if entry["status"] == "待确认":
            message += "（旅客等待数据缺失，先挂待确认，不许直接放行）"
        if deduped:
            message = f"同一摆渡车重复登记同一趟次，已按时间去重只留最近一条；{message}"
        return entry, message

    # ---------- 趟次动作 ----------

    def run_action(
        self, entry_id: int, action: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"摆渡趟次 {entry_id} 不存在或已归档"
        terminal = str(entry.get("航站楼") or "")
        standard = TERMINAL_STANDARDS.get(terminal)
        status = str(entry.get("status") or "")

        if action == "补录等待":
            if status in CLOSED_STATUSES:
                return None, f"趟次{status}，不能再补录等待数据"
            wait = _to_int(values.get("旅客等待时长"))
            if wait is None or wait < 0:
                return None, "补录等待需填写非负的旅客等待时长（分钟）"
            entry["旅客等待时长"] = wait
            boarding_raw = values.get("上车人数")
            if boarding_raw is not None and str(boarding_raw).strip() != "":
                boarding = _to_int(boarding_raw)
                if boarding is None or boarding < 0:
                    return None, "上车人数需为非负整数"
                entry["上车人数"] = boarding
            if standard is None:
                return None, f"航站楼 {terminal} 未配置发车标准，无法判定能否发车"
            entry["status"] = self._evaluate(entry, standard)
            self._sync_flags(entry)
            return entry, f"等待数据已补录，趟次转入「{entry['status']}」"

        if action == "处置超时":
            if status != "超时待处置":
                return None, f"趟次当前状态为「{status}」，只有超时待处置的趟次需要处置"
            entry["status"] = "待发车"
            entry["处置说明"] = str(values.get("处置说明") or "").strip() or "值班调度已处置超时等待"
            self._sync_flags(entry)
            return entry, "超时趟次已处置，可以安排发车"

        if action == "确认发车":
            if status == "待确认":
                return None, "旅客等待数据缺失，趟次挂在待确认，不许直接放行，请先补录等待数据"
            if status == "超时待处置":
                threshold = standard["等待阈值分钟"] if standard else "?"
                return None, f"旅客等待超过 {terminal} 约定阈值 {threshold} 分钟，必须先处置再发车"
            if status in CLOSED_STATUSES:
                reason = "不能重复发车" if status == "已发车" else "不能发车"
                return None, f"趟次{status}，{reason}"
            if standard is None:
                return None, f"航站楼 {terminal} 未配置发车标准，无法判定能否发车"
            boarding = _to_int(entry.get("上车人数")) or 0
            if boarding < standard["最小发车人数"]:
                return None, (
                    f"上车人数 {boarding} 人，未达 {terminal} 最小发车人数 "
                    f"{standard['最小发车人数']} 人，暂不能发车"
                )
            entry["status"] = "已发车"
            entry["发车时间"] = _now()
            self._sync_flags(entry)
            return entry, "趟次已确认发车"

        if action == "取消趟次":
            if status in CLOSED_STATUSES:
                return None, f"趟次{status}，不能取消"
            entry["status"] = "已取消"
            self._sync_flags(entry)
            return entry, "趟次已取消"

        return None, f"动作「{action}」不属于摆渡车可执行范围"

    # ---------- 航站楼标准 ----------

    def list_standards(self) -> list[dict[str, Any]]:
        return [
            {"航站楼": terminal, **standard}
            for terminal, standard in sorted(TERMINAL_STANDARDS.items())
        ]

    def update_standard(self, terminal: str, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        terminal = terminal.strip().upper()
        standard = TERMINAL_STANDARDS.get(terminal)
        if standard is None:
            return None, f"航站楼 {terminal} 未配置发车标准"
        for field in STANDARD_FIELDS:
            raw = values.get(field)
            if raw is None or str(raw).strip() == "":
                continue
            number = _to_int(raw)
            if number is None or number < 0:
                return None, f"{field}需为非负整数"
            standard[field] = number
        return {"航站楼": terminal, **standard}, f"{terminal} 发车标准已更新"

    # ---------- 内部判定 ----------

    def _evaluate(self, entry: dict[str, Any], standard: dict[str, int]) -> str:
        """按等待数据与约定阈值给趟次定状态；人数是否达标在确认发车时再卡。"""
        wait = _to_int(entry.get("旅客等待时长"))
        if wait is None:
            return "待确认"
        if wait > standard["等待阈值分钟"]:
            return "超时待处置"
        return "待发车"

    def _sync_flags(self, entry: dict[str, Any]) -> None:
        """pending 与「待发车」保持一致，运营概览的待发车数才能和趟次明细对上。"""
        entry["pending"] = entry.get("status") == "待发车"
        entry["abnormal"] = entry.get("status") == "超时待处置"
