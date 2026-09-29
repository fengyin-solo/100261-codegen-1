"""摆渡车业务规则：趟次发车判断、等待超时处理、运力下限校验与重复登记去重。

发车判断综合「上车人数」与「旅客等待时长」：等待数据缺失的趟次挂「待确认」不许直接放行；
等待超过航站楼约定阈值的趟次必须先处理再发车；可用摆渡车少于当天需求下限时不许排新趟次。
各航站楼的阈值与下限分开设置。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "shuttle"

# 各航站楼发车标准：等待阈值（分钟）、上车人数下限、摆渡车需求下限。
# 各航站楼分开设置，互不影响。
TERMINAL_STANDARDS: dict[str, dict[str, Any]] = {
    "T1": {"等待阈值": 20, "上车人数下限": 10, "摆渡车需求下限": 3},
    "T2": {"等待阈值": 15, "上车人数下限": 8, "摆渡车需求下限": 5},
    "T3": {"等待阈值": 25, "上车人数下限": 12, "摆渡车需求下限": 2},
}

# 摆渡车台账：车辆状态决定可用运力（可用车辆才能投入排班）。
FLEET: list[dict[str, Any]] = [
    {"摆渡车编号": "BASC-B001", "车辆状态": "可用"},
    {"摆渡车编号": "BASC-B002", "车辆状态": "可用"},
    {"摆渡车编号": "BASC-B003", "车辆状态": "可用"},
    {"摆渡车编号": "BASC-B004", "车辆状态": "可用"},
    {"摆渡车编号": "BASC-B005", "车辆状态": "维修中"},
    {"摆渡车编号": "BASC-B006", "车辆状态": "维修中"},
]

REQUIRED_FIELDS = ["趟次编号", "航站楼", "摆渡车编号", "上车人数", "发车日期"]
STATUS_DEPARTING = "待发车"
STATUS_CONFIRM = "待确认"
STATUS_DEPARTED = "已发车"
STATUSES = [STATUS_DEPARTING, STATUS_CONFIRM, STATUS_DEPARTED]
TERMINALS = list(TERMINAL_STANDARDS.keys())
ACTION_DEPART = "发车"
ACTION_HANDLE = "处理"
ACTIONS = [ACTION_DEPART, ACTION_HANDLE]


def _available_buses() -> int:
    return sum(1 for bus in FLEET if bus.get("车辆状态") == "可用")


def _standard(terminal: str) -> dict[str, Any] | None:
    return TERMINAL_STANDARDS.get(terminal)


def _wait_minutes(row: dict[str, Any]) -> int | None:
    value = row.get("旅客等待时长")
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _boarding(row: dict[str, Any]) -> int:
    try:
        return int(row.get("上车人数", 0))
    except (TypeError, ValueError):
        return 0


def _recompute(row: dict[str, Any]) -> None:
    """根据当前字段重算状态、等待超时与标记，保证状态与趟次明细一致。"""
    terminal = str(row.get("航站楼") or "")
    standard = _standard(terminal)
    wait = _wait_minutes(row)
    handled = bool(row.get("handled"))

    wait_exceeded = False
    if standard is not None and wait is not None:
        wait_exceeded = wait > int(standard["等待阈值"])
    row["wait_exceeded"] = wait_exceeded

    if row.get("status") == STATUS_DEPARTED:
        row["pending"] = False
        row["abnormal"] = False
        return

    if wait is None:
        # 旅客等待数据缺失：挂起待确认，不许直接放行。
        row["status"] = STATUS_CONFIRM
        row["pending"] = False
        row["abnormal"] = True
        return

    row["status"] = STATUS_DEPARTING
    row["pending"] = True
    row["abnormal"] = wait_exceeded and not handled


def _departure_blockers(row: dict[str, Any]) -> list[str]:
    """返回阻止发车的原因列表；为空表示可以发车。"""
    blockers: list[str] = []
    terminal = str(row.get("航站楼") or "")
    standard = _standard(terminal)
    wait = _wait_minutes(row)
    boarding = _boarding(row)

    if wait is None:
        blockers.append("旅客等待数据缺失，已挂起待确认，不许直接放行")
        return blockers

    if standard is not None:
        threshold = int(standard["等待阈值"])
        if wait > threshold and not bool(row.get("handled")):
            blockers.append(f"等待时长 {wait} 分钟超过阈值 {threshold} 分钟，必须先处理再发车")
        min_boarding = int(standard["上车人数下限"])
        if boarding < min_boarding:
            blockers.append(f"上车人数 {boarding} 人未达下限 {min_boarding} 人，不能发车")
    return blockers


class ShuttleService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        terminal: str | None = None,
        date: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = list(store.rows(MODULE))
        if keyword:
            rows = [
                r for r in rows
                if keyword in str(r.get("趟次编号", "")) or keyword in str(r.get("摆渡车编号", ""))
            ]
        if terminal:
            rows = [r for r in rows if r.get("航站楼") == terminal]
        if date:
            rows = [r for r in rows if r.get("发车日期") == date]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"

        terminal = str(values.get("航站楼") or "").strip()
        standard = _standard(terminal)
        if standard is None:
            return None, f"航站楼 {terminal} 未设置发车标准，无法排趟次"

        available = _available_buses()
        floor = int(standard["摆渡车需求下限"])
        if available < floor:
            short = floor - available
            return None, (
                f"可用摆渡车 {available} 辆，低于{terminal}当天需求下限 {floor} 辆，"
                f"还差 {short} 辆，暂不能排新趟次"
            )

        # 同一辆摆渡车重复登记同一趟次：按时间去重，只留最近一条记录。
        bus_no = str(values.get("摆渡车编号") or "").strip()
        trip_no = str(values.get("趟次编号") or "").strip()
        rows = store.rows(MODULE)
        rows[:] = [
            r for r in rows
            if not (str(r.get("摆渡车编号")) == bus_no and str(r.get("趟次编号")) == trip_no)
        ]

        entry = {"id": max((int(r.get("id", 0)) for r in rows), default=0) + 1}
        for field in REQUIRED_FIELDS:
            entry[field] = values.get(field)
        entry["旅客等待时长"] = values.get("旅客等待时长")
        entry["handled"] = False
        _recompute(entry)
        rows.append(entry)
        return entry, ""

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"摆渡趟次 {entry_id} 不存在或已归档"
        for key, value in values.items():
            if key in ("id", "status", "pending", "abnormal", "handled", "wait_exceeded"):
                continue
            entry[key] = value
        _recompute(entry)
        return entry, ""

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"摆渡趟次 {entry_id} 不存在或已归档"
        if action not in ACTIONS:
            return None, f"动作「{action}」不属于摆渡车可执行范围"

        if action == ACTION_DEPART:
            if entry.get("status") == STATUS_DEPARTED:
                return None, "该趟次已发车，无需重复操作"
            blockers = _departure_blockers(entry)
            if blockers:
                return None, blockers[0]
            entry["status"] = STATUS_DEPARTED
            entry["pending"] = False
            entry["abnormal"] = False
            return entry, "已发车"

        if action == ACTION_HANDLE:
            if entry.get("status") == STATUS_DEPARTED:
                return None, "该趟次已发车，无需处理"
            wait = _wait_minutes(entry)
            standard = _standard(str(entry.get("航站楼") or ""))
            if wait is None:
                return None, "该趟次等待数据缺失，需先补录等待数据再处理"
            if standard is None or wait <= int(standard["等待阈值"]):
                return None, "该趟次未超等待阈值，无需处理"
            if bool(entry.get("handled")):
                return None, "该趟次已处理过，可直接发车"
            entry["handled"] = True
            _recompute(entry)
            return entry, "已处理等待超时，可发车"

        return None, f"动作「{action}」不可执行"

    def stats(
        self,
        *,
        keyword: str | None = None,
        terminal: str | None = None,
        date: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """当前筛选批次的状态分布与人数合计，供页面与导出保持同一口径。"""
        rows, _ = self.list_entries(
            keyword=keyword, terminal=terminal, date=date, status=status, page=1, size=10000
        )
        counts = {
            STATUS_DEPARTING: sum(1 for r in rows if r.get("status") == STATUS_DEPARTING),
            STATUS_CONFIRM: sum(1 for r in rows if r.get("status") == STATUS_CONFIRM),
            STATUS_DEPARTED: sum(1 for r in rows if r.get("status") == STATUS_DEPARTED),
        }
        return {"counts": counts, "total_people": sum(_boarding(r) for r in rows)}

    def export_entries(
        self,
        *,
        keyword: str | None = None,
        terminal: str | None = None,
        date: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, int]:
        items, total = self.list_entries(
            keyword=keyword, terminal=terminal, date=date, status=status, page=1, size=10000
        )
        return items, total, sum(_boarding(r) for r in items)

    def get_standards(self) -> dict[str, dict[str, Any]]:
        return TERMINAL_STANDARDS

    def update_standard(self, terminal: str, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        if terminal not in TERMINAL_STANDARDS:
            return None, f"航站楼 {terminal} 未设置发车标准"
        for key in ("等待阈值", "上车人数下限", "摆渡车需求下限"):
            if key in values and values[key] is not None:
                try:
                    TERMINAL_STANDARDS[terminal][key] = int(values[key])
                except (TypeError, ValueError):
                    return None, f"标准「{key}」必须是整数"
        return TERMINAL_STANDARDS[terminal], ""
