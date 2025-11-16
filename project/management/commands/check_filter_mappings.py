import re
from pathlib import Path
from types import SimpleNamespace

from django.core.management.base import BaseCommand


class DummyQueryDict:
    """简单的 QueryDict 替身，用于调用 filter_config.* 函数。

    所有 get/getlist 都返回默认值或空列表，只为构造配置结构，
    不关心实际参数值。
    """

    def get(self, key, default=None):  # pragma: no cover - 简单代理
        return default

    def getlist(self, key):  # pragma: no cover - 简单代理
        return []


def _build_dummy_request():
    return SimpleNamespace(GET=DummyQueryDict())


def _extract_expected_params(filter_config_dict):
    """从筛选配置中提取预期出现的 GET 参数名集合。"""
    expected = set()

    def handle_filter(f):
        name = f.get("name")
        if not name:
            return
        f_type = f.get("type", "text")
        if f_type in {"text", "select"}:
            expected.add(name)
        elif f_type == "daterange":
            expected.add(f"{name}_start")
            expected.add(f"{name}_end")
        elif f_type == "number":
            expected.add(f"{name}_min")
            expected.add(f"{name}_max")

    for f in filter_config_dict.get("quick_filters", []):
        handle_filter(f)

    for group in filter_config_dict.get("advanced_filter_groups", []):
        for f in group.get("filters", []):
            handle_filter(f)

    return expected


def _extract_view_params(file_path: Path):
    """从视图源码中解析实际使用到的 request.GET 参数名。"""
    source = file_path.read_text(encoding="utf-8")
    pattern_get = re.compile(r"request\.GET\.get\(\s*'([^']+)'")
    pattern_getlist = re.compile(r"request\.GET\.getlist\(\s*'([^']+)'")
    params = set(pattern_get.findall(source)) | set(pattern_getlist.findall(source))
    return params


class Command(BaseCommand):
    help = "检查 filter_config 中定义的筛选字段与各列表视图 GET 参数的映射情况。"

    def handle(self, *args, **options):  # pragma: no cover - 管理命令入口
        from project import filter_config

        project_dir = Path(__file__).resolve().parents[2]
        contracts_view = project_dir / "views_contracts.py"
        procurements_view = project_dir / "views_procurements.py"

        request = _build_dummy_request()

        contract_cfg = filter_config.get_contract_filter_config(request)
        procurement_cfg = filter_config.get_procurement_filter_config(request)

        contract_expected = _extract_expected_params(contract_cfg)
        procurement_expected = _extract_expected_params(procurement_cfg)

        contract_used = _extract_view_params(contracts_view)
        procurement_used = _extract_view_params(procurements_view)

        # 视图里会使用的通用参数，这里不作为“未在配置中定义”的异常
        common_params = {
            "q",
            "q_mode",
            "page",
            "page_size",
            "sort",
            "order",
            "year",
            "global_year",
            "project",
            "global_project",
            "status",
        }

        self.stdout.write("== 合同列表筛选字段映射检查 ==")
        self._report_mismatches("合同", contract_expected, contract_used, common_params)

        self.stdout.write("")
        self.stdout.write("== 采购列表筛选字段映射检查 ==")
        self._report_mismatches("采购", procurement_expected, procurement_used, common_params)

    def _report_mismatches(self, label, expected, used, common_params):
        missing_in_view = sorted(expected - used)
        extra_in_view = sorted((used - expected) - common_params)

        if not missing_in_view and not extra_in_view:
            self.stdout.write(self.style.SUCCESS(f"[{label}] 所有配置字段均已在视图中使用，没有发现不一致。"))
            return

        if missing_in_view:
            self.stdout.write(self.style.WARNING(f"[{label}] 配置中存在但视图未使用的参数:"))
            for name in missing_in_view:
                self.stdout.write(f"  - {name}")

        if extra_in_view:
            self.stdout.write(self.style.WARNING(f"[{label}] 视图中使用但配置中未声明为筛选字段的参数:"))
            for name in extra_in_view:
                self.stdout.write(f"  - {name}")
