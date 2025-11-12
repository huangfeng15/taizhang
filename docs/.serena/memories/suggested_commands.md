# 常用命令（Windows PowerShell）

- 列出文件: `ls` 或 `Get-ChildItem`
- 查看文件: `Get-Content -LiteralPath "文件名.md" -Raw -Encoding UTF8`
- 全文搜索（ripgrep）: `'rg -n "关键词|正则" "D:\\develop\\new pachong yangguangcaigou\\taizhang\\docs"'`
  - 注意: 外层单引号，内层双引号，避免转义冲突。
- 按文件名搜索（fd 如可用）: `fd -H -t f "\.md$" .`
- Serena 搜索: 使用 `search_for_pattern` 按相对路径与 glob 精准定位内容。
- 编码确认: `file -bi`（若可用），或在编辑器中统一设为 UTF-8（无 BOM）。
