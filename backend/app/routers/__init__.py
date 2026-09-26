"""业务模块路由汇总。

这里统一按别名导入再暴露 ROUTERS：模块名有可能和内置名撞车（某个业务模块就叫 dict、list
这种名字时），按名字直接 import 会把内置类型覆盖掉，函数注解在运行时求值就会报
'module' object is not subscriptable。
"""
from __future__ import annotations

from app.routers import flightstand as router_flightstand
from app.routers import marshalling as router_marshalling
from app.routers import bridge as router_bridge
from app.routers import baggage as router_baggage
from app.routers import catering as router_catering
from app.routers import fueling as router_fueling
from app.routers import deicing as router_deicing
from app.routers import lavatory as router_lavatory
from app.routers import pushback as router_pushback
from app.routers import gse as router_gse
from app.routers import cargo as router_cargo
from app.routers import clearance as router_clearance
from app.routers import turnaround as router_turnaround
from app.routers import ramp as router_ramp
from app.routers import weather2 as router_weather2
from app.routers import vehicle as router_vehicle
from app.routers import staffshift as router_staffshift
from app.routers import runway as router_runway
from app.routers import emergencyplan as router_emergencyplan
from app.routers import qualitycheck as router_qualitycheck

ROUTERS = [router_flightstand, router_marshalling, router_bridge, router_baggage, router_catering, router_fueling, router_deicing, router_lavatory, router_pushback, router_gse, router_cargo, router_clearance, router_turnaround, router_ramp, router_weather2, router_vehicle, router_staffshift, router_runway, router_emergencyplan, router_qualitycheck]
