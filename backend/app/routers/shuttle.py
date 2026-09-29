"""摆渡车接口：趟次登记、发车判断、等待超时处理、运力校验与当天清单导出。

列表与导出共用同一套筛选口径，保证导出清单上的人数合计与页面同一批趟次对得上。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload
from app.services.shuttle import ShuttleService

router = APIRouter(prefix="/api/shuttle", tags=["摆渡车"])

service = ShuttleService()

LIST_FIELDS = ["趟次编号", "航站楼", "摆渡车编号", "上车人数", "旅客等待时长", "发车日期", "计划发车时间"]
STATUSES = ["待发车", "待确认", "已发车"]
TERMINALS = ["T1", "T2", "T3"]


@router.get("")
def list_entries(
    keyword: str | None = Query(default=None, description="按趟次或摆渡车编号检索"),
    terminal: str | None = Query(default=None, description="T1、T2、T3"),
    date: str | None = Query(default=None, description="发车日期 YYYY-MM-DD"),
    status: str | None = Query(default=None, description="待发车、待确认、已发车"),
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """按航站楼、日期与状态过滤摆渡趟次；同时返回当前批次的人数合计与状态分布。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(
        keyword=keyword, terminal=terminal, date=date, status=status, page=page, size=size
    )
    stats = service.stats(keyword=keyword, terminal=terminal, date=date, status=status)
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "counts": stats["counts"],
        "total_people": stats["total_people"],
    }


@router.get("/export")
def export_entries(
    keyword: str | None = Query(default=None),
    terminal: str | None = Query(default=None),
    date: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    """导出当天发车清单：返回与页面同一筛选批次的全量数据及人数合计。"""
    items, total, total_people = service.export_entries(
        keyword=keyword, terminal=terminal, date=date, status=status
    )
    return {
        "module": "shuttle",
        "total": total,
        "total_people": total_people,
        "items": items,
    }


@router.get("/standards")
def get_standards() -> dict[str, Any]:
    """读取各航站楼分开设置的发车标准。"""
    return {"standards": service.get_standards()}


@router.put("/standards/{terminal}")
def update_standard(terminal: str, payload: EntryPayload) -> ActionResult:
    """更新某航站楼的发车标准（等待阈值、上车人数下限、摆渡车需求下限）。"""
    standard, message = service.update_standard(terminal, payload.values)
    if standard is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"{terminal} 发车标准已更新", entry=standard)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条摆渡趟次明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"摆渡趟次 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条摆渡趟次：校验运力下限，重复登记按时间去重，等待数据缺失挂待确认。"""
    entry, message = service.create_entry(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="摆渡趟次已登记", entry=entry)


@router.put("/{entry_id}", response_model=ActionResult)
def update_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """更新趟次字段（如补录等待数据），更新后重算发车判断。"""
    entry, message = service.update_entry(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="摆渡趟次已更新", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条趟次执行发车或处理；不满足条件的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
