# MiWear Firmware Archives 镜像仓库

本仓库是 [AstralSightStudios/MiWearFirmwareArchives](https://github.com/AstralSightStudios/MiWearFirmwareArchives) 的自动同步镜像，
用于归档小米 / Redmi / 米家 / 米动等品牌智能手环、手表的官方固件包（全量包 + 增量包），
并通过 GitHub Actions 定时（每日 10:00 北京时间）自动检测上游新 Release 并同步。

> **⚠️ 重要提示**：本仓库**不生产、不修改**任何固件，仅做归档与镜像分发。
> 固件版权归原始厂商（小米 / 华米等）所有，详情见文末[免责声明](#免责声明)。

---

## 仓库内容

| 项目 | 数值 |
|---|---|
| 固件设备数 | 46 款 |
| Release 总数 | 83 |
| 固件资产总数 | 208（全量包 83 + 增量包 125） |
| 总大小 | ~10.2 GB |
| 同步策略 | 每日自动检测上游新 Release（cron: 每日 10:00 UTC+8）+ 手动触发 |

所有固件以 **GitHub Release** 形式分发（固件体积大，不适合放入 Git 仓库本体）。

---

## 文件名命名规则

文件名格式统一为：

```
{设备代号}_{版本号}_full_{内容哈希}.bin                                  ← 全量包
{设备代号}_{目标版本号}_from_{源版本号}_incremental_{内容哈希}.bin        ← 增量包
```

| 组成部分 | 含义 | 示例 |
|---|---|---|
| `设备代号` | 设备在小米穿戴固件体系内的代号 | `miwear.watch.p67cn` |
| `_full_` | 全量包，可独立刷入，不依赖旧版本 | `miwear.watch.p67cn_v3.101.043_full_a4ce8564.bin` |
| `_from_旧版本_` | 增量包，**只能从标注的旧版本升级**到目标版本 | `miwear.watch.p67cn_v3.101.043_from_v3.101.036_incremental_c8151bdf.bin` |
| 末尾 8 位十六进制 | 文件内容哈希，用于区分同一版本的多个包 | `a4ce8564` |

**使用建议**：
- 想稳定刷机 → 优先选 `_full_` 全量包；
- 想省流量小升级 → 选与当前版本匹配的 `_from_你的版本_` 增量包；
- 增量包有严格版本依赖，选错会刷机失败，请核对当前设备版本。

---

## 设备代号对照表

代号是小米穿戴体系内部的设备标识（如 `miwear.watch.xxx`），与市售名称的对应关系如下。
资料参考：[wearwiki 小米可穿戴设备代号表](https://wearwiki.coratech.cc/wiki/sheets/xiaomi-wearable-codes.html)、[米坛知识库](https://wiki.bandbbs.cn)、[小米/米家产品库](https://home.miot-spec.com/s/watch)。

### 手环

| 设备代号 | 市售名称 |
|---|---|
| `miwear.watch.m66` | 小米手环 8 |
| `miwear.watch.m66nfc` | 小米手环 8 NFC |
| `miwear.watch.n66cn` | 小米手环 9 |
| `miwear.watch.n66nfc` | 小米手环 9 NFC |
| `miwear.watch.n66tc` | 小米手环 9 陶瓷特别版 |
| `miwear.watch.n66gl` | 小米手环 9（海外版） |
| `miwear.watch.n67cn` | 小米手环 9 Pro |
| `miwear.watch.o66cn` | 小米手环 10 |
| `miwear.watch.o66nfc` | 小米手环 10 NFC |
| `miwear.watch.o66tc` | 小米手环 10 陶瓷版 |
| `miwear.watch.o66lj` | 小米手环 10 耀影金特别版 |
| `miwear.watch.p67cn` | 小米手环 10 Pro |
| `miwear.watch.p67tc` | 小米手环 10 Pro 陶瓷版（官方欢迎语：小米手环10 Pro 陶瓷版） |
| `miwear.watch.p67gln` | 小米手环 10 Pro NFC 版（官方欢迎语：小米手环10 Pro NFC版） |
| `miwear.watch.n69cn` | Redmi 手环 3 |
| `mijia.watch.m69` | Redmi 手环 2 |
| `mijia.watch.band01` | Redmi 手环（初代） * |
| `lchz.watch.m67` | 小米手环 8 Pro（官方欢迎语：小米手环 8 Pro） |
| `lchz.watch.m67ys` | 小米手环 8 Pro 原神定制版（官方欢迎语：小米手环8 Pro 原神定制版） |

### 手表（小米 Watch / REDMI Watch）

| 设备代号 | 市售名称 |
|---|---|
| `mijia.watch.n62` | 小米手表 S3 |
| `mijia.watch.n62lte` | 小米手表 S3 eSIM 版 |
| `mijia.watch.n62car` | 小米手表 S3 SU7 限定版（官方欢迎语：Xiaomi Watch S3 eSIM，硬件为 eSIM 版） |
| `mijia.watch.n62cg` | 小米手表 S3 SU7 限定版（同 n62car，官方欢迎语同为 Xiaomi Watch S3 eSIM） |
| `mijia.watch.o62` | 小米手表 S4 |
| `mijia.watch.o62lte` | 小米手表 S4 eSIM 版 |
| `mijia.watch.o62m` | 小米手表 S4 15 周年版（XRING INSIDE，官方欢迎语：Xiaomi Watch S4 eSIM，硬件为 eSIM 版） |
| `miwear.watch.o63` | 小米手表 S4（41mm） |
| `mijia.watch.n62s` | 小米手表 S4 Sport |
| `miwear.watch.p62` | 小米手表 S5（46mm） |
| `miwear.watch.p62lte` | 小米手表 S5 eSIM（46mm） |
| `lchz.watch.n65` | REDMI Watch 4 |
| `miwear.watch.o65` | REDMI Watch 5 |
| `miwear.watch.o65m` | REDMI Watch 5 eSIM（XRING INSIDE） |
| `miwear.watch.p65` | REDMI Watch 6 |
| `hqbd3.watch.l67` | 小米手环 7 Pro（类手表形态） |

### 其他 / 待确认

| 设备代号 | 推测 / 说明 |
|---|---|
| `midr.watch.ds` | 小米手表 Color（官方更新说明标题：小米手表Color） |
| `lchz.watch.m65s` | 未知，lchz 系列（Redmi Watch 4 Active 一带）* |
| `midr.watch.k62` / `k63` / `k65` / `m62a` / `m62s` / `sports` | midr 系列，暂未查到公开对照 * |
| `mijia.watch.l61` | 未知 * |
| `mijia.watch.v1` | 未知 * |
| `mj1205.motion.ecg` | 推测为米家系心电/血压类设备 * |

> `*` 标注为推测或未证实；其余已确认项均与上游官方固件 Release 版本介绍中的开机欢迎语（「欢迎使用 XXX」）交叉核对，欢迎提交 PR 补充准确对照。

---

## 使用教程

### 1. 这些文件是什么

固件文件是 `.bin` 格式的**设备固件镜像**（小米手环/手表运行的系统），由小米官方发布，本仓库只做归档。

- **全量包**（`_full_`）：完整固件镜像，**不依赖当前版本**，推荐刷机首选；
- **增量包**（`_from_旧版本_incremental_`）：差分升级包，体积小，但**只能从文件名里标注的旧版本升级**，版本不匹配会刷机失败。

### 2. 怎么下载

进入仓库 **Releases** 页面（页面右侧 Releases 栏），按设备/版本找到对应 tag，点开即可看到该版本的全部文件，点文件名直接下载。

也可以命令行批量下载（以全量包为例）：

```bash
# 下载某个 Release 的全部资产
gh release download firmware-miwear.watch.p67cn-v3.101.043-xxxxxxxx -R hrk666666/firmware-archives-public

# 或浏览器直链下载单个文件
curl -L -O https://github.com/hrk666666/firmware-archives-public/releases/download/firmware-miwear.watch.p67cn-v3.101.043-xxxxxxxx/miwear.watch.p67cn_v3.101.043_full_a4ce8564.bin
```

### 3. 怎么刷入设备

本仓库**只提供固件文件**，刷入请使用支持的工具：

- **AstroBox**（开源工具箱，Windows/Linux）：连接设备 → 导入本仓库下载的 `.bin` 文件 → 工具会自动识别设备与固件 → 校验通过后通过蓝牙推送刷入。支持小米/Redmi/米家系列。
- 部分设备也可参考 **OronBox** 等社区工具（支持从小米健康日志导入设备，免登录）。
- 官方渠道：小米运动健康 App 会自动推送固件更新（仅正式版，无法选择版本）。

> 使用第三方工具刷机前请先备份设备数据；国行/海外版固件**不要混刷**（硬件可能不同）。

### 4. 注意事项

- **增量包版本严格匹配**：刷增量包前务必确认设备当前固件版本与文件名中 `_from_` 标注的版本一致；
- **固件校验**：部分工具会校验固件完整性（哈希），请从 Releases 页面直接下载，不要经第三方转存；
- **降级风险**：部分设备可能限制降级（拒绝低于出厂版本的固件），失败属正常现象；
- **变砖风险**：刷机中断（电量不足/蓝牙断开）可能导致设备无法开机，风险自行承担。

---

## 同步机制

- 工作流文件：`.github/workflows/sync-releases.yml`
- 核心脚本：`.github/workflows/sync.sh`
- 触发方式：
  - 定时：每日 10:00（UTC+8）自动运行
  - 手动：仓库 Actions 页面 → `Sync upstream releases` → `Run workflow`
- 逻辑：对比上游 `AstralSightStudios/MiWearFirmwareArchives` 与本地 Release 的 tag 列表，
  只同步新增的 Release（幂等，重复运行不产生重复 Release）。

---

## 免责声明

1. **固件版权**：本仓库中所有固件文件的版权归原始厂商（小米科技有限责任公司、华米科技等）及其关联方所有。
   本仓库不拥有、不主张任何固件知识产权，固件内容以官方发布版本为准。
2. **镜像性质**：本仓库仅为公开固件的**归档镜像**，用于个人学习、研究与数据备份目的。
   固件均来自上游开源归档项目，未做任何修改。
3. **刷机风险**：刷写固件（尤其增量包）存在变砖、数据丢失、保修失效等风险。
   刷机属于高风险操作，**请自行承担全部风险**；本仓库作者与维护者对因使用本仓库内容造成的任何损失不承担责任。
4. **版权方要求**：如您是固件版权方，认为本仓库的镜像行为侵犯了您的权益，请通过 GitHub Issue 联系，
   我们将在核实后第一时间下架相关内容。
5. **非官方声明**：本仓库与小米、Redmi、米家、华米等品牌**无任何关联、授权或赞助关系**，
   未经任何厂商认可、背书或代理。
6. **合规提醒**：请遵守所在地法律法规。建议优先通过官方渠道（小米运动健康 App 等）获取和更新固件。

---

## 许可证

仓库元数据（README、工作流脚本）以 MIT 许可证发布。
固件文件本身遵循其原始版权方的条款，与本仓库许可证无关。

## 相关链接

- 上游归档项目：[AstralSightStudios/MiWearFirmwareArchives](https://github.com/AstralSightStudios/MiWearFirmwareArchives)
- 开源刷机工具 AstroBox：[AstralSightStudios/AstroBox-NG](https://github.com/AstralSightStudios/AstroBox-NG)
