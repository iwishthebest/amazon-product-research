# Amazon 多站点时区协调第一轮实施计划

> **For agentic workers:** Execute this plan task-by-task in the current checkout with test-first changes.

**Goal:** 让 AU、US 站点按各自业务时区生成稳定、可区分的日报，同时保留北京时间作为操作员总览时区。

**Architecture:** 数据库存储和采集时间继续使用带时区的 UTC。每个站点通过独立配置指定 IANA 时区、输出目录和本地业务日期。Windows 任务由统一分发脚本按站点本地时间决定是否执行，报告文件按站点目录和业务日期隔离。

**Tech Stack:** Python 3、`zoneinfo`、PowerShell、SQLite、pytest。

## Global Constraints

- 不引入新的第三方依赖。
- 不修改或覆盖现有未提交业务改动。
- 站点日期使用 `Australia/Sydney` 和 `America/Los_Angeles`，操作员时区使用 `Asia/Shanghai`。
- 所有生成文件必须包含站点代码和站点业务日期，避免跨站点覆盖。

---

### Task 1: 建立站点时区配置和本地日期解析

**Files:**
- Create: `amazon_release/site_config.py`
- Modify: `config.example.json`
- Test: `tests/test_site_config.py`

**Interfaces:**
- `load_sites(path) -> dict[str, SiteConfig]`
- `SiteConfig.local_date(now_utc=None) -> str`
- `SiteConfig.is_due(now_utc=None) -> bool`

- [ ] 写测试覆盖 AU 和 US 的 IANA 时区、夏令时日期、`run_local_time` 到期判断。
- [ ] 运行 `pytest tests/test_site_config.py -q`，确认新接口缺失导致失败。
- [ ] 实现最小配置读取和时区计算，不引入固定 UTC 偏移。
- [ ] 重新运行该测试并确认通过。

### Task 2: 统一采集脚本的站点日期和输出目录

**Files:**
- Modify: `scripts/daily_collect.ps1`
- Modify: `scripts/daily_delivery.ps1`
- Modify: `amazon_release/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- CLI 保持现有 `--timezone` 兼容，同时支持按站点传入显式时区和独立输出目录。
- PowerShell 脚本默认不再隐式使用纽约时区，AU/US 调用必须显式传入站点参数。

- [ ] 写回归测试，证明传入 `Asia/Shanghai` 时文件日期为北京时间日期，且 CLI 不读取主机本地日期。
- [ ] 运行目标测试确认失败。
- [ ] 修改脚本和 CLI，使日期、采集和报告使用同一站点时区。
- [ ] 运行 CLI 和脚本相关测试确认通过。

### Task 3: 添加按站点本地时间执行的分发器

**Files:**
- Create: `scripts/daily_dispatch.ps1`
- Modify: `scripts/register_tasks.ps1`
- Test: `tests/test_daily_dispatch.py`

**Interfaces:**
- 分发器每次运行读取站点配置，按站点 `run_local_time` 和本地业务日期决定是否执行。
- 每站点生成独立输出路径 `data/reports/<site>/<business_date>`。

- [ ] 写测试覆盖同一站点同一业务日只允许一次执行，以及 AU/US 跨时区日期不同的情况。
- [ ] 运行测试确认分发器接口缺失导致失败。
- [ ] 实现幂等运行账本和 PowerShell 调用，Windows 任务改为每 30 分钟触发分发器。
- [ ] 运行分发器测试和现有全量测试。

### Task 4: 文档和验证

**Files:**
- Modify: `README.md`

- [ ] 补充配置示例、报告路径和北京时间总览规则。
- [ ] 运行 `pytest -q`、`python -m compileall amazon_release scripts`。
- [ ] 检查 `git diff --check` 和工作区变更范围。
