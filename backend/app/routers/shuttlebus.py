"""摆渡车接口：维护摆渡趟次，覆盖登记趟次、补录等待、处置超时、确认发车、取消趟次等动作。

注意路由顺序：/export、/standards 这类固定路径要写在 /{entry_id} 前面，
否则会被当成 entry_id 匹配掉，导出和标准设置就拿不到了。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload
from app.services.shuttlebus import ShuttlebusService

router = APIRouter(prefix="/api/shuttlebus", tags=["摆渡车"])

service = ShuttlebusService()

LIST_FIELDS = ["趟次编号", "航站楼", "摆渡车编号", "上车人数", "旅客等待时长", "登记时间", "服务日期", "趟次状态"]
STATUSES = ["待确认", "待发车", "超时待处置", "已发车", "已取消"]


@router.get("")
def list_entries(
    keyword: str | None = Query(default=None, description="按趟次编号检索"),
    status: str | None = Query(default=None, description="待确认、待发车、超时待处置、已发车、已取消"),
    terminal: str | None = Query(default=None, description="按航站楼过滤，如 T1"),
    date: str | None = Query(default=None, description="按服务日期过滤，格式 YYYY-MM-DD"),
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """按趟次编号、状态、航站楼、服务日期过滤趟次列表。

    除统一的 items/total/page/size 外，附带本批趟次（全部筛选结果，非单页）的
    上车人数合计与状态计数，页面统计卡片和导出清单都以此为准。
    """
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total, passenger_total, status_counts = service.list_entries(
        keyword=keyword, status=status, terminal=terminal, service_date=date, page=page, size=size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "passenger_total": passenger_total,
        "status_counts": status_counts,
    }


@router.get("/export")
def export_entries(
    keyword: str | None = Query(default=None, description="按趟次编号检索"),
    status: str | None = Query(default=None, description="趟次状态过滤"),
    terminal: str | None = Query(default=None, description="按航站楼过滤"),
    date: str | None = Query(default=None, description="按服务日期过滤，格式 YYYY-MM-DD"),
) -> dict[str, Any]:
    """导出发车清单：与列表同一套筛选口径，人数合计与页面上同一批趟次对得上。"""
    items, total, passenger_total = service.export_entries(
        keyword=keyword, status=status, terminal=terminal, service_date=date
    )
    return {
        "module": "shuttlebus",
        "total": total,
        "passenger_total": passenger_total,
        "items": items,
    }


@router.get("/standards")
def list_standards() -> dict[str, Any]:
    """读取各航站楼的发车标准（最小发车人数、等待阈值、需求下限、可用车辆）。"""
    return {"items": service.list_standards()}


@router.put("/standards/{terminal}", response_model=ActionResult)
def update_standard(terminal: str, payload: EntryPayload) -> ActionResult:
    """分开设置单个航站楼的发车标准；非法取值会被拦下并说明原因。"""
    standard, message = service.update_standard(terminal, payload.values)
    if standard is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=standard)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条摆渡趟次明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"摆渡趟次 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """排新趟次：校验必填字段、航站楼标准与可用车下限，重复登记按时间去重。"""
    entry, message = service.create_entry(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条趟次执行补录等待、处置超时、确认发车、取消趟次；不合规的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
