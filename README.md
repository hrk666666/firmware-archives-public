# 小米穿戴固件存档镜像

自动同步自 [AstralSightStudios/MiWearFirmwareArchives](https://github.com/AstralSightStudios/MiWearFirmwareArchives)（AstroBox 固件共享计划存储库）。

> 本仓库通过 GitHub Actions 定时同步上游全部固件 Release，**新设备 / 新固件版本发布后自动同步**（每天 UTC 02:00 + 可手动触发）。

## 固件内容

全部固件以 **GitHub Releases** 形式存放（与上游一致），命名规范：

| 类型 | 命名 | 说明 |
|------|------|------|
| 全量包 | `<产品>_<版本>_full_<hash>.bin` | 完整固件，可独立刷入 |
| 增量包 | `<产品>_<版本>_from_<旧版本>_incremental_<hash>.bin` | 差分升级包，需基于指定旧版本 |

Release tag 规范：`firmware-<产品>-<版本>-<hash>`

## 查看固件

打开 [Releases](../../releases) 页面，按产品/版本浏览下载。

支持的设备产品前缀（节选）：

- `miwear.watch.*` — 小米 Watch 系列（p62/p65/p67/n66/n67/o63/o65/o66/m66 等）
- `mijia.watch.*` — 米家手表系列（band01/l61/m69/n62/o62/v1 等）
- `midr.watch.*` — 红米手表系列（ds/k62/k63/k65/m62/sports 等）
- `lchz.watch.*` — 米兔/儿童手表系列
- `mj1205.motion.ecg` — 小米手环 ECG

## 手动触发同步

仓库 Actions 页面 → **Sync Firmware Releases** → **Run workflow** → 立即执行一次全量/增量同步。

## 免责声明

固件版权归原厂商所有，本仓库仅作存档备份用途。
