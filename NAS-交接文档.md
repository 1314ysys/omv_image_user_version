# NAS 系统交接文档

> 目标机：OpenMediaVault 8.6.0-1 "Synchrony"（Debian 13 trixie，内核 6.12.113+deb13-amd64）
> 交付形态：系统盘 raw 镜像 `omv-nas.img.zst`（Rufus DD 模式写 U 盘）
> 文档版本：v3.2（网卡自适应 + UEFI/BIOS 双引导 + 空闲区清零重打包，体积较旧版小 45%）
> 出厂默认密码：**`NasAdmin2026!`**（root 与 OMV admin，首启强制改密）

---

## 1. 概览

这套系统由三层组成：

| 层 | 提供者 | 作用 |
|---|---|---|
| 存储与系统管理层 | **OpenMediaVault 8.6**（Debian 13） | Web 面板、用户/权限、磁盘与文件系统、SMB/NFS、插件体系 |
| 数据冗余层 | **mergerfs + SnapRAID** | 把多块数据盘合成一个池；用一块校验盘做快照式冗余 |
| 应用层 | **Docker + Compose**（14 个容器） | 影音、照片、文件、反代、导航页、AI 网关 |

**没有任何功能来自破解或第三方定制镜像**：系统本体是 OMV 官方源，插件是 OMV 官方插件源 + omvextrasorg，所有应用都是各自项目的**官方上游镜像**。清单见 §3。

---

## 2. 硬件与磁盘布局（原始测试机）

| 设备 | 容量 | 角色 | 文件系统 / UUID |
|---|---|---|---|
| `/dev/sdX` | 24 GB | **系统盘** | ① `/` ext4 `f9924bbe-…`（22.7 GB）② ESP FAT32 `4DA6-50A7`（400 MB）③ swap `c5845499-…`（908 MB） |
| `/dev/sda` | 4 GB | 数据盘 data1 | ext4 `2c21fd2f-…` |
| `/dev/sdb` | 6 GB | 数据盘 data2 | ext4 `b7a7cc4d-…` |
| `/dev/sdd` | 8 GB | 数据盘 data3 | ext4 `16581d2d-…` |
| `/dev/sde` | 9 GB | 校验盘 parity1 | ext4 `9e7ef799-…` |

- 合并池挂载点：`/srv/mergerfs/pool`（fuse.mergerfs，UUID `aee1bb88-…`）
- 应用配置目录：**`/srv/appdata`（在系统盘上）** —— 这是本次交付刻意改的，见 §9.2
- RAM 4 GB / swap 908 MB，虚拟化平台识别为 VMware
- 系统盘的设备名**每次开机都可能变**（实测 `sdc`/`sdd`/`sde`/`sda` 都当过系统盘），所以下表写 `sdX`；所有引用一律按 UUID

> ⚠️ 镜像里**只有系统盘**。数据盘（sda/sdb/sdd/sde）不属于镜像内容，接收方必须自己准备磁盘并重建池与 SnapRAID。

---

## 3. 组件来源总表（"这个功能是什么来的"）

### 3.1 系统与存储（deb 包，均来自官方源）

| 功能 | 软件包 | 版本 | 来源 |
|---|---|---|---|
| Web 管理面板 / 系统核心 | `openmediavault` | 8.6.0-1 | OMV 官方源 |
| 配置引擎（RPC + Salt） | `openmediavault-salt` | 8.1.0 | OMV 官方源 |
| 存储池（多盘合一） | `openmediavault-mergerfs`（mergerfs） | 8.0.4 | OMV 官方源 |
| 快照式冗余校验 | `openmediavault-snapraid`（snapraid） | 8.0.3 | OMV 官方源 |
| 容器编排 | `openmediavault-compose`（docker + compose） | 8.2.5 | OMV 官方源 |
| Docker 引擎 | `docker-ce` | 29.9.2 | Docker 官方 apt 源 |
| SMB / CIFS 共享 | `openmediavault` 内置 samba 状态 | — | OMV 官方源 |
| DLNA 媒体广播 | `openmediavault-minidlna` | 8.1 | OMV 官方源 |
| 病毒扫描 | `openmediavault-clamav` | 8.0.3-1 | OMV 官方源 |
| 登录爆破防护 | `openmediavault-fail2ban` | 8.0 | OMV 官方源 |
| 共享文件夹根目录 | `openmediavault-sharerootfs` | 8.0.1-1 | OMV 官方源 |
| 终端（Web 内） | `openmediavault-cterm` | 8.0.5 | OMV 官方源 |
| 第三方插件源聚合 | `openmediavault-omvextrasorg` | 8.0.4 | omvextras.org |
| 国内 apt 镜像 | 阿里云 `mirrors.aliyun.com` | — | 已写进 `/etc/apt/sources.list.d/` |

### 3.2 应用层（docker 镜像，均取自各项目官方上游）

| 服务 | 镜像 | 版本 | 端口 | 数据目录 |
|---|---|---|---|---|
| 影音服务器 | `jellyfin/jellyfin` | 10.11.2 | 8096 | `/srv/appdata/jellyfin` |
| 豆瓣刮削插件 | MetaShark（GitHub `cxfksword/jellyfin-plugin-metashark`） | 2.3.8.0 | — | 同上 `config/plugins/` |
| 成人内容刮削插件 | MetaTube（GitHub `metatube-community/jellyfin-plugin-metatube`） | 2025.1102.2200.0 | — | 同上 |
| MetaTube 服务端 | `ghcr.io/metatube-community/metatube-server` | latest | 8088→8080 | `/srv/appdata/metatube` |
| 照片备份 | `ghcr.io/immich-app/immich-server` + `-machine-learning` + `postgres` + `redis` | v2 系 | 2283 | `/srv/appdata/immich` |
| 反向代理 / 证书 | `jc21/nginx-proxy-manager` | latest | 8080 / 8181 / 8443 | `/srv/appdata/compose/npm` |
| 导航页 | `gethomepage/homepage` | latest | 3000 | `/srv/appdata/compose/homepage` |
| 文件列表 + WebDAV | `openlistteam/openlist` | v4 系 | 5244（`/dav`） | `/srv/appdata/openlist` |
| 内网穿透客户端 | `fatedier/frp`（frpc） | latest | — | `/srv/appdata/compose/frpc` |
| AI 网关①Qoder | `ghcr.io/shuishuipingan/qoder2api-hub` | latest | 8601→8790 | `/srv/appdata/qoder2api-hub` |
| AI 网关②opencode | `ghcr.io/jasonxu114514/opencode2api` | v1.4.5 | 8602→8080、8603→8081 | `/srv/appdata/opencode2api` |
| AI 网关③WorkBuddy | `ghcr.io/ithtelab/workbuddy-manager` | latest | 8604→7864 | `/srv/appdata/workbuddy-manager` |
| AI 网关④FreeLLM | `ghcr.io/tashfeenahmed/freellmapi` | latest | 8605→3001 | `/srv/appdata/freellmapi` |

> `crowdsec` compose 项目留有目录但未启用（磁盘与内存不足，8 GB 起）。

---

## 4. 存储栈：mergerfs + SnapRAID

```
数据盘 sda+sdb+sdd  ──mergerfs──▶  /srv/mergerfs/pool   （对外统一的池）
                          └─ 真实目录：/srv/dev-disk-by-uuid-<uuid>/
校验盘 sde          ──SnapRAID──▶  parity（单盘可恢复任意一块数据盘）
```

- SnapRAID 阵列名 `nas`，内容文件 `content` 放在 data1 + data2 两块盘上（双份，防单盘丢失）
- `autosave 0`、`nohidden`；排除规则：`*.unrecoverable lost+found/ aquota.* /tmp/ .content *.bak /snapraid.conf*`
- **每小时** `snapraid sync`（cron），校验通过 `snapraid scrub`
- mergerfs 挂载选项必须保持 **path-preserving 关闭**，否则 SnapRAID 看到的路径与池路径不一致，恢复会失败

**常用命令**

```bash
snapraid sync          # 同步校验（新增/修改数据后）
snapraid scrub -p 10   # 抽查 10% 校验
snapraid status        # 健康状态
snapraid diff          # 与上次同步的差异
```

---

## 5. 服务清单与访问入口

| 服务 | 地址 | 说明 |
|---|---|---|
| OMV 管理面板 | `http://<IP>/` | 存储 / 用户 / 插件 / 容器 |
| 导航页 Homepage | `http://<IP>:3000/` | 所有服务的统一入口 |
| Jellyfin 影音 | `http://<IP>:8096/` | 首次访问走建库向导 |
| Immich 照片 | `http://<IP>:2283/` | 首次访问走管理员创建向导 |
| Nginx Proxy Manager | `http://<IP>:8181/` | 管理端口；对外反代用 8080/8443 |
| OpenList 文件 | `http://<IP>:5244/` | WebDAV 端点为 `/dav` |
| MetaTube 服务端 | `http://<IP>:8088/` | Jellyfin 插件后端，无需人访问 |
| qoder2api-hub | `http://<IP>:8601/` | OpenAI 兼容端点 `/v1` |
| opencode2api API | `http://<IP>:8602/v1` | OpenAI 兼容端点 |
| opencode2api 控制台 | `http://<IP>:8603/` | 模型 / Key 管理 |
| workbuddy-manager | `http://<IP>:8604/` | 面板（上游未部署，功能受限） |
| freellmapi | `http://<IP>:8605/` | OpenAI 兼容端点 `/v1` |

**只有 `:80` 和 `:8181` 应该暴露到公网。** 四个 AI 网关内含凭据，必须留在内网或被 NPM 加一层认证。

---

## 6. 出厂凭据（净化后的状态）

| 对象 | 账号 | 密码 | 首登处理 |
|---|---|---|---|
| 系统 root | `root` | `NasAdmin2026!` | **首启强制改密**（首启脚本执行 `chage -d 0 root`） |
| OMV 面板 | `admin` | `NasAdmin2026!` | 请立即手动修改（未强制过期，避免面板锁死） |
| OpenList | `admin` | `NasAdmin2026!` | 已是管理员（role=2，权限 65535） |
| Jellyfin | — | — | **无账号**，首次访问自建管理员 |
| Immich | — | — | **无账号**，首次访问自建管理员 |
| NPM | `admin@example.com` | `changeme` | NPM 出厂值，登录后按提示改 |
| opencode2api 控制台 | `admin` | `NasAdmin2026!` | 本地 Key 见 `/srv/appdata/compose/opencode2api/config.json` |
| workbuddy-manager | `admin` | `NasAdmin2026!` | 见 compose 内 `WB_ADMIN_PASSWORD` |
| freellmapi | `admin@nas.local` | `NasAdmin2026!` | 见 `compose/freellmapi/.env` |
| qoder2api-hub | `admin` | — | API Key 明文在 `docker logs qoder2api-hub` |
| Samba | — | — | **无任何 Samba 用户**，共享需自行重建 |

> ⚠️ 镜像所有副本共用同一套默认密码与同一套 AI 网关 API Key。**分发后请立即修改**，或按 §11 重新生成。
> 密码强度限制（踩过坑）：`workbuddy-manager` 要求 ≥12 位且非常见弱口令；`opencode2api` 要求 ≥10 位。

---

## 7. 本次做的两套自动化

### 7.1 首启初始化 `/usr/local/sbin/nas-firstboot.sh`

由 `nas-firstboot.service`（oneshot，已 enable）在**每台机器的第一次开机**执行一次，标记文件 `/var/lib/nas/.firstboot-done`：

1. 重新生成 `/etc/machine-id`（否则所有克隆体 ID 相同）
2. 重新生成 SSH 主机密钥（否则所有克隆体共用同一私钥）
3. **网卡名自动适配**（镜像里写的是 `ens33`）：扫描 `/sys/class/net` 取第一块物理网卡，若与 `/etc/network/interfaces` 不符就**重写该文件并重启网络**，原文件备份为 `interfaces.bak`。换主板后网卡叫 `enp3s0`/`eno1` 也能自己拿到 IP
4. 等 DHCP 拿到地址（最多 30 秒），用 `ip route get 1.1.1.1` 取地址（比 `hostname -I` 可靠）
5. `chage -d 0 root` —— 强制 root 首次登录改密
6. **把配置里写死的旧 IP 换成当前 IP**：导航页 `services.yaml`、MetaTube 插件 `<Server>`，并重跑一次自动发现
7. **拉起全部应用**：`systemctl enable --now docker` + 遍历 `/srv/appdata/compose/*/` 执行 `docker compose up -d`（镜像内容器是停止状态，靠这一步恢复，见 §10）
8. 把「首次启动必须做的三件事」写到 `/etc/motd`（控制台开机可见），最后写标记文件

> 服务单元已改成 `After=local-fs.target` + `Wants=network.target`，**开机约 15 秒即执行**（旧版排在 `network-online.target` 后面，要等 3 分钟）。
> **分发前必须删掉 `/var/lib/nas/.firstboot-done`**，否则接收方会跳过上面全部初始化。

### 7.2 导航页自动发现 `/usr/local/sbin/homepage-autodiscover.py`

- 由 `/etc/cron.d/homepage-autodiscover` **每 15 分钟**执行
- 扫描 `docker ps` 中所有**已发布到 0.0.0.0 的端口**，把尚未手工收录的容器自动补进 Homepage 的「自动发现」分组
- 只维护 `# >>> AUTO-DISCOVER … # <<< AUTO-DISCOVER` 之间那段，手工条目不受影响
- 排除表：`homepage / npm / jellyfin / immich_server / openlist / qoder2api-hub / opencode2api / workbuddy-manager / freellmapi`（这些已手工收录）
- 实测有效：部署 MetaTube 后它自动把 `metatube:8088` 加进了导航页

手工加服务时改 `/srv/appdata/compose/homepage/config/services.yaml`；分组顺序在 `settings.yaml` 的 `layout:`。

---

## 8. 净化清单（这次到底删了什么）

| 项目 | 处理结果 |
|---|---|
| 系统用户 `nasuser`（uid 1000，原唯一 sudo/Samba 用户） | **已删除**，OMV 用户库同步移除 |
| Samba 账号 | **已清空**（`pdbedit -L` 为空） |
| Samba 共享 media/photos/backup | **已删除**，`smb.conf` 只剩 `[global]` |
| sudo 组成员 | **空** |
| Jellyfin 账号与媒体库 | **已删**（`config/data`、`config/config`），插件与插件配置保留 |
| Immich 数据库与上传 | **已清空**，回到安装向导 |
| NPM 数据与证书 | **已清空**，回到 `admin@example.com/changeme` |
| OpenList 数据库/配置 | **已重建**，只留一个 admin（`NasAdmin2026!`） |
| 四个 AI 网关状态 | **已清空**，账号/Key/用量全部重置 |
| 数据盘内容（media/photos/backup） | **已清空**，保留空目录骨架 |
| frpc 配置 | **已脱敏**为占位（serverAddr / token 为空） |
| swap 分区 | **整段零写后用原 UUID 重建**（清掉内存残留后又保留 fstab UUID） |
| `/root/.bash_history`、`/tmp`、`/var/log/*`、容器日志 | **已清空**（成像脚本冻结前再清一次） |
| 旧目录 `_removed_webdav`、`webdav` 容器 | **已删除** |

**保留的（按你的选择）**：四个 AI 网关、Jellyfin + MetaShark + MetaTube 插件、NPM（重置为出厂）、Immich、OpenList、Homepage、SnapRAID/mergerfs 存储栈。

---

## 9. 镜像与分发（方案 A：系统盘 raw 镜像）

### 9.1 制品

| 项 | 值 |
|---|---|
| 文件 | `omv-nas.img.zst` |
| 压缩后大小 | **3.95 GiB**（4,241,872,599 字节）—— 比旧版 gzip 成品（6.91 GiB）小 **45%** |
| 解压后大小 | **24 GiB**（25,769,803,776 字节，整个系统盘，含分区表） |
| SHA256（压缩包） | `2a799d76d8dcb57a38d8783856d39df92bffb625fcc6dd5edd27905a8133a1b6` |
| SHA256（解压后 .img） | `6c03eb7f792a3359c9ebeca5b42f3d227c08a3932c0a4e85ad54c5b1c3760874` |
| 系统盘内分区 | ① ext4 `/` 22.7 GB　② **EFI 系统分区 400 MB (FAT32, label=ESP)**　③ swap 908 MB |
| 分区表 / 引导 | **MBR（dos）** + **UEFI 与 Legacy BIOS 双引导**（ESP 里放了 shim→grub 签名链，见 §9.3.1） |
| 最小目标盘 | **24 GiB**（25,769,803,776 字节）；建议 ≥32 GB |
| Windows 副本 | `D:\omv-nas.img.zst` |
| 校验状态 | 流式解压校验通过：还原字节数 **25,769,803,776**（与原始系统盘逐字节相符），zstd 帧校验和通过 |

> **设备名会变，UUID 不会。** 同一份镜像在不同主板/VM 上，系统盘可能从 `sda` 变成 `sde`（实测四次重启里系统盘分别叫过 `sdc`、`sde`、`sdd`、`sda`）。
> 镜像内 `/etc/fstab`、mergerfs 池、SnapRAID content 全部按 **UUID** 引用，所以盘序变化不影响启动与挂载——这也是镜像能跨机器分发的前提。
> 空闲区已用零填充（写入 10,910 MB 零后删除），因此镜像里**不含已删除数据的残留**，既压得更小也不会泄露构建期的文件内容。

### 9.2 为什么 appdata 放在系统盘

原始部署把 `/srv/appdata` 放在 mergerfs 池上（数据盘）。**成像前已迁到系统盘** `/srv/appdata`，原因：

- 镜像只含系统盘；若配置留在池上，接收方烧录后容器会全部因缺配置而失败
- appdata 仅约 **335 MB**，放系统盘完全放得下（根盘 14 G 已用 / 7.7 G 可用）
- 所有 compose 与自动发现脚本中的 `/srv/mergerfs/pool/appdata` → `/srv/appdata` 已批量改写（13 个文件）
- 仍指向池的只有**媒体路径**：Jellyfin `/srv/mergerfs/pool/media`、OpenList `/srv/mergerfs/pool`——接收方建好池后自然生效；池不存在时 Docker 会自动建空目录，服务照常启动

### 9.3 写入 U 盘（Windows / Rufus）

1. Windows 上先**解压**：装 7-Zip（≥21.02，24.x 都行）→ 右键 `omv-nas.img.zst` →「提取到当前文件夹」→ 得到 `omv-nas.img`（**需要 24 GiB 空闲空间**）
   - 命令行方式：`zstd -d omv-nas.img.zst`（官方 zstd for Windows / Linux 均可）
   - 若压缩软件版本太老打不开 `.zst`（WinRAR 不支持 zstd），装 7-Zip 或 zstd 即可
2. 插入 **≥32 GB** U 盘（24 GiB 镜像 + 余量）
3. 打开 Rufus → 设备选 U 盘 →「选择」选 `omv-nas.img`
4. 分区类型选 **MBR**；目标系统 **「UEFI（非 CSM）」或「BIOS（或 UEFI-CSM）」都可以**——镜像两种引导都有：MBR 里有 BIOS 引导代码，400 MB 的 ESP 里有 UEFI 的 `\EFI\BOOT\BOOTX64.EFI`（shim 签名链），所以**纯 UEFI 主板、开了 Secure Boot 的机器也能直接起**
5. 弹出提示时务必选 **「以 DD 镜像模式写入」**（不是 ISO 模式；DD 模式按字节写入，Rufus 的分区类型选项此时只是界面选项，但保持 MBR 不容易点错）
6. 写入完成后从 U 盘启动目标机，首启过程见 §9.4

> Rufus **不能**直接读 `.zst`/`.gz`，必须先解压成 `.img`。Linux 下也可以 `zstd -dc omv-nas.img.zst | dd of=/dev/sdX bs=8M status=progress`（免落地解压）。

### 9.3.1 换机器还剩哪些限制

| 项 | 状态 |
|---|---|
| **引导方式** | ✅ **不再限制**。UEFI（含 Secure Boot 开）与 Legacy BIOS 都实测启动成功 |
| **网卡名** | ✅ **不再限制**。首启脚本自动识别真实网卡名并重写 `/etc/network/interfaces`（§7.1 第 3 步） |
| **目标盘容量** | ⚠️ 必须 **≥ 24 GiB**。用 ≥32 GB 盘；更大的盘写完后 `growpart /dev/sdX 1 && resize2fs /dev/sdX1` 扩展 `/`（ESP 与 swap 在盘尾，扩展第 1 分区时注意别覆盖它们，必要时先 `parted` 调整顺序） |
| **Secure Boot** | ✅ 已内置 Debian 签名的 `shimx64.efi` + `grubx64.efi`，**与 Secure Boot 开关状态无关**（开/关都能起） |
| **BIOS 里没有启动项** | 无 NVRAM 条目也能起：ESP 里同时放了兜底路径 `\EFI\BOOT\BOOTX64.EFI` |


### 9.3.2 没有数据盘时，系统实际会怎样

镜像里**只有系统盘**。mergerfs 池不是"数据"，而是开机时把几块真实磁盘合起来的**挂载点**——那些盘不在，就没有池：

| 对象 | 没有数据盘时的真实表现 |
|---|---|
| `/etc/fstab` 4 条数据盘 | 都带 `nofail`，**启动不受影响**；UUID 不存在 → 挂载点不出现 |
| mergerfs 池 `srv-mergerfs-pool.mount` | `RequiresMountsFor=` 那 4 个 UUID → 依赖不满足，**单元启动失败，池不存在**；系统进 `degraded` 但能正常用 |
| `/srv/mergerfs/pool` | 系统盘上就是个**普通空目录**（`root:users 2775`），池挂不上也不会消失，容器照样启动 |
| Jellyfin / OpenList | 启动正常，但媒体路径落在这个空目录 → 视频**静默写进 22.7 GB 系统盘**，不报错 |
| OMV 面板 | 「存储 → 文件系统」列出 4 条**缺失/不可用**记录；SnapRAID 阵列 `nas` 报磁盘缺失 |
| SnapRAID 定时任务 | 每小时 sync 持续报错（不影响系统） |

**接上自己的盘之后**：OMV 里删掉这 4 条旧文件系统记录和 SnapRAID 阵列 → 用新盘重建（§11「重建数据盘与池」）→ 再把 Jellyfin 媒体路径指到新池。

### 9.4 首次开机必须做的事

1. 开机约 **15 秒**，首启脚本自动跑完：机器标识、SSH 密钥、网卡自适应、强制改密、IP 改写、**自动拉起全部容器**
2. 控制台会显示 **`/etc/motd`** 提示，上面写着当前 IP
3. 用 root 登录（密码 `NasAdmin2026!`），会被强制要求改密
4. 若 motd 上 IP 显示「未获取到」：控制台 `ip -br link` 看真实网卡名 → 改 `/etc/network/interfaces` → `systemctl restart networking`（正常情况下第 1 步已自动处理）
5. 浏览器进 `http://<IP>/`，用 `admin / NasAdmin2026!` 登录 OMV → 改密码、改固定 IP
6. **接数据盘 → OMV「存储」里建文件系统 → 建 mergerfs 池 → 配 SnapRAID**（镜像不含数据盘，见 §9.3.2）
7. 进 Jellyfin `:8096` 建管理员与媒体库；进 Immich `:2283` 建管理员
8. 需要 SMB 共享就自己在「服务 → SMB」里加（当前没有共享、没有 Samba 用户），先建一个 OMV 用户并勾选 SMB

> 容器状态检查：`docker ps --format '{{.Names}}\t{{.Status}}'` 应有 **14 个**、全部 `healthy` 或 `Up`。

### 9.5 开机不会卡死的保障

- `/etc/fstab` 里四块数据盘都带 **`nofail`**，缺盘不影响启动
- 只有系统盘 `/` 与 swap 是必需项
- 首启脚本只做幂等操作，失败不会阻塞启动（`nas-firstboot.service` 是 oneshot，无强依赖）

---

## 10. 已知坑（都踩过了）

| 坑 | 现象 | 处理 |
|---|---|---|
| `github.com` / `releases/download` 被墙 | 装插件、拉脚本全失败 | 前缀镜像 `https://ghfast.top/`（备选 `ghproxy.net`、`gh-proxy.com`）；`raw.githubusercontent.com` 可直连 |
| Docker Hub / ghcr 拉取慢或失败 | `pull` 超时 | `daemon.json` 配 `registry-mirrors`（`docker.m.daocloud.io`、`docker.1panel.live` 等）；ghcr 用 `ghcr.nju.edu.cn` 前缀 |
| **OMV 会重写 `daemon.json`** | DNS / 镜像源配置莫名消失，容器内域名解析失败 | 保留 `dns: ["192.168.99.1","223.5.5.5","119.29.29.29"]` 与 `registry-mirrors`；不要用 systemctl restart docker 之外的粗暴方式改 |
| OpenList 首次初始化**只有禁用的 guest，没有 admin** | CLI `admin set` 静默无效 | 直接写 `data.db`：`INSERT x_users` + `role=2` + `permission=65535`；密码哈希 = `sha256(sha256(pw+"-https://github.com/alist-org/alist")+"-"+salt)` |
| OpenList WebDAV 403 / 405 | 权限位为 0；Local 驱动 `302_redirect` 生成空链接 | `permission=65535`（含 bit8 WebDAV 读）；`webdav_policy=native_proxy` |
| Jellyfin 10.11 插件需严格匹配 ABI | 装老版本插件直接不加载 | MetaShark 2.3.8.0 ↔ abi 10.11；MetaTube `2025.1102.2200.0` ↔ abi 10.11 |
| MetaTube 插件默认指向 `127.0.0.1:8088` | 插件装好但刮不到 | 必须单独跑 `metatube-server` 容器，并把插件 `Server` 指到 `<主机IP>:8088` |
| `metatube-server` 容器内监听 **8080** | 映射 8088:8088 死活连不上 | 映射写成 `8088:8080` |
| workbuddy 密码策略 | 容器反复重启，日志 `至少 12 位` | 用 ≥12 位强密码 |
| opencode2api 密码策略 + 目录属主 | 反复重启：`webui.password must contain at least 10 characters` / `permission denied` | 密码 ≥10 位；数据目录属主必须与容器内 uid 一致（100:101） |
| workbuddy 数据目录属主 | `目录不可写：/app/data` | `chown -R 10001:10001` |
| `chage -d 0` 的副作用 | root 下次 SSH 登录被强制先改密，脚本化操作会卡住 | 交付时保留强制改密；**自动化脚本里不要对 root 用 `chage -d 0`** |
| heredoc 里 `set -u` + `$(...)` | `python3 - <<EOF` 提前展开导致语法错 | heredoc 一律用 `<<'EOF'` 加引号 |
| 容器日志/无 `curl` | Guest 上没装 curl | 用 `python3` urllib 或 `wget` |
| **容器崩溃循环会疯狂写 core dump** | workbuddy 启动失败后反复重启，每次落一个几十 MB~GB 的 `core.<pid>`，累计 **254 个 / 15.9 GB**，把根盘可用从 2 GB 打到 0，连带 immich、opencode2api、freellmapi 全部 `No space left on device` | 先 `docker update --restart=no <c>` 止血再排查；在 compose 里加 `ulimits: {core: 0}` **永久关闭该容器的 core dump**（workbuddy 已加） |
| **别用 `find -name 'core.*' -delete` 清 core** | 会误匹配 `click/core.py`、`ajv/dist/core.js`、`core.cpython-312.pyc` 这类正常模块，把 docker **镜像层**里的文件一起删掉，事后容器报 `ModuleNotFoundError: No module named 'click.core'` | 用 `-name 'core.[0-9]*' -size +10M` 精确匹配；或先 `find ... -printf '%s %p\n'` 核对再删 |
| 误删镜像层后 `rmi` + `pull` 修不好 | 明明 `Status: Downloaded newer image`，文件仍缺失 | 本地还有**同源镜像的另一个 tag**（如 `ghcr.nju.edu.cn/...`）共享同一层，层不释放，pull 直接复用坏层。必须把该仓库**所有 tag 全部 rmi** → `docker image prune -f` → 再 pull |
| **宿主磁盘满会直接搞死运行中的 VM** | 宿主盘写满 → VMware 无法写 vmem/vmdk，日志 `Error writing log ... Disk full?` → `vmx` 进程 `0xc0000005` 访问违例崩溃 → VM 假死（CPU 归零、SSH 不通、`vmrun` 所有子命令挂起） | 先腾宿主空间；再用 UIAutomation 找到 `#32770` 崩溃对话框、向「确定」按钮发 `BM_CLICK` 释放文件锁；之后 `vmrun start`。**成像前确认宿主剩余空间 ≥ 镜像体积 ×1.5** |
| 强杀 VM 后容器起不来 ≠ 数据坏了 | 一批容器 `Restarting`，日志五花八门（ENOSPC / 数据库打不开 / 启动失败） | 多数是**磁盘被打满**导致的连带失败；腾出空间后 `docker compose up -d --force-recreate` 即可，不必重建数据 |
| **`sfdisk`/`fdisk` 改分区表会连带清掉 MBR 里的 GRUB 代码** | 分区改完能挂载，但目标机 BIOS 启动黑屏（找不到引导） | 改完分区必须重装 BIOS 引导：`grub-install --target=i386-pc --recheck --no-floppy /dev/sdX`（需要 `grub-pc-bin`） |
| 重划分区后 `blkid` 还报旧 swap UUID | 新分区上仍留着旧 swap 签名，`blkid` 读出的是 swap UUID，写进 fstab 的 ESP 行变成 swap UUID → `mount /boot/efi` 报 `wrong fs type` | 格式化前先 `wipefs -a /dev/sdX2`；格式化后再用 `blkid -s UUID -o value` 取真正的 VFAT UUID（形如 `4DA6-50A7`） |
| **VMware 关机时会重写 `.vmx`** | 手动加 `firmware = "efi"` 后重启，仍按 BIOS 启动——设置在关机瞬间被覆盖 | 必须**等 `vmware-vmx` 进程完全退出**再改 vmx，改完 `Select-String` 确认；切 UEFI 时同时删掉旧 `.nvram`（BIOS 变量残留会挡住 EFI 变量） |
| `rm -rf /var/cache/*` 会删掉 OMV 的 apt 归档目录 | 之后所有 `apt` 操作报 `Problem executing scripts DPkg::Pre-Invoke`、`Building local package repository` 失败 | 清缓存别用通配符；删了就先 `mkdir -p /var/cache/openmediavault/archives` 再装包 |
| **`fsfreeze -f /` + 长时网络流式取像会卡死** | 冻结根盘后往 SSH 管道里 `dd \| zstd`，跑到 23 分钟 / 6.5 GB 时数据完全停住，SSH 登录被 PAM 挂住（登录卡在密码提示） | 分布取像改成「停 docker + 停容器 + `sync` + **不冻结**」流式读取；需要一致性时再考虑 `fsfreeze`，但别跨越十几分钟的网络传输 |
| 容器在镜像里是「已停止」状态 → 接收方开机不自动起 | `restart: unless-stopped` 的语义是「除非被显式停过」，被 stop 过的容器开机不会自动启动，14 个容器全躺着 | 首启脚本里补 `systemctl enable --now docker` + 遍历 compose 目录 `docker compose up -d`（已加，见 §7.1 第 7 步） |
| **首启标记必须删掉才能分发** | `/var/lib/nas/.firstboot-done` 留在镜像里，接收方开机会跳过全部初始化：机器标识重复、SSH 密钥相同、root 不强制改密、网卡不适配 | 成像前 `rm -f /var/lib/nas/.firstboot-done`；本机自己用的话拍完镜像再 `date -Is > 标记` 重建 |
| 空闲区清零会不会撑爆宿主盘 | 取决于 vmdk 稀疏度：本次 `system.vmdk` 已 23,853 MB / 虚拟 24,576 MB（近乎满分配），写 10,910 MB 零后宿主 **0 增长** | 清零前先看 `system.vmdk` 体积与虚拟容量差多少；差值就是最坏增长量，宿主剩余空间要大于它 |
| 压缩格式与压缩比的选择 | 同一份 24 GiB 内容：`gzip -6` 26 MB/s 但体积大；`xz -6` 只有 5 MB/s（24 GiB 要 84 分钟）；`zstd -12` 26 MB/s、`zstd -15/-19` 压缩比几乎不再提升而速度腰斩 | 取像用 **`zstd -12`**（16~20 分钟）；`.zst` 用 7-Zip ≥21.02 或 `zstd -d` 解开，`.xz` 兼容性最好但慢 4 倍 |

---

## 11. 运维手册

### 常用命令

```bash
# 容器
docker ps -a
cd /srv/appdata/compose/<stack> && docker compose up -d

# OMV 配置应用
omv-rpc -u admin "Config" "applyChanges" '{"modules":["samba"],"force":true}'
omv-salt deploy run samba          # 注意：salt 模块名是 samba，不是 smb

# 存储
snapraid sync && snapraid status

# 导航页自动发现（手动跑一次）
/usr/local/sbin/homepage-autodiscover.py
```

### 想换掉镜像里共用的 AI Key

```bash
# opencode2api：改 config.json 的 server_keys / webui.password 后重建
cd /srv/appdata/compose/opencode2api && docker compose down && docker compose up -d
# qoder2api-hub：清空 accounts 后重建，新 Key 在 docker logs 里
rm -rf /srv/appdata/qoder2api-hub/accounts/* && docker restart qoder2api-hub
# freellmapi：改 .env 后重建
# workbuddy：改 compose 里的 WB_ADMIN_PASSWORD 后重建
```

### 重建数据盘与池（接收方第一次用）

1. OMV → 存储 → 磁盘 → 选中新盘 → 擦除
2. 存储 → 文件系统 → 创建 ext4（每块数据盘）
3. 存储 → mergerfs → 新建池，挂载点 `/srv/mergerfs/pool`，**不要**启用 path-preserving
4. 存储 → SnapRAID → 新建阵列 `nas`，选校验盘 + 数据盘，`content` 选两块数据盘
5. 建共享文件夹 `media/photos/backup`（指向池），再建 OMV 用户并勾 SMB
6. Jellyfin 媒体路径改为池上的媒体目录

---

## 12. 功能"壳子"说明（别当成坏了）

| 服务 | 现状 |
|---|---|
| qoder2api-hub | 容器正常，但 `accounts=0`；必须自己用 OAuth 登录 Qoder 加账号才有上游能力 |
| opencode2api | 容器正常、模型目录能拉（146 个），但上游按 IP 限流，实际调用常见 429/403 |
| workbuddy-manager | 面板正常，但上游 `workbuddy2api` 不是公开项目，反代地址是占位，实际业务不可用 |
| freellmapi | 容器正常，`0 keys`，需要自己填各家免费 Key |
| frpc | 占位配置，填了 serverAddr/token 才能用 |
| NPM | 无任何代理主机与证书，需要自己加 |
| Tailscale / CrowdSec | 未启用 |

---

## 13. 构建期事故与恢复记录（2026-10-29）

> 这一节记录成像之后发生在**构建机/测试机**上的事故与恢复过程。**交付镜像不受影响**——镜像在事故前 12 分钟冻结完成，事故后重新校验 SHA256 仍与冻结时一致。

### 13.1 事件链

| 时间 | 事件 |
|---|---|
| 08:21 | 二次成像完成，`gzip -t` 通过，SHA256 = `2c02fc94…82e6e4` |
| 08:25 | 宿主机拔取镜像到 Windows，宿主 **E 盘被写满**（VM 磁盘 vmdk 19.5 GB + 数据盘增长 + 4 GB vmem 挤在一起） |
| 08:33 | VMware 无法写 vmem/vmdk → 日志 `Error writing log. Disk full?` → `vmx` 进程 `0xc0000005` 崩溃 → **VM 假死**（CPU 归零、SSH 断、`vmrun` 全部挂起） |
| 08:47 | 清出 8.9 GB（删 pnpm 缓存）；用 UIAutomation 点掉 VMware 崩溃对话框，文件锁释放 |
| 08:52 | `vmrun start` 恢复；VM 正常启动，**首启脚本自动执行**（machine-id、SSH 密钥全部重建，root 强制改密）——这等于把 §7 的自动化实测了一遍 ✅ |
| 08:59 | 发现容器批量 `Restarting`：WORKBUDDY 崩溃循环在 docker 层里写了 **254 个 core dump / 15.9 GB**，把根盘打满，连带 immich/opencode2api/freellmapi 全部 ENOSPC |
| 09:20 | 清理 core、重建受损容器、重拉被误伤的镜像 → 14/14 容器全部 healthy |
| 09:24 | 镜像副本 SHA256 比对一致，交付完成 |

### 13.2 三个值得记住的教训

1. **core dump 能吃掉整块盘**：崩溃循环的容器每次重启都落一个 core 文件，几分钟就是十几 GB。已给 workbuddy 的 compose 加 `ulimits: {core: 0}` 永久关闭。
2. **`find -name 'core.*'` 是陷阱**：它会连 `click/core.py`、`ajv/dist/core.js` 一起删，损坏的是**镜像层**而不是容器层。修复必须把该镜像的**所有 tag**（含 `ghcr.nju.edu.cn` 副本）全删再 pull，否则 docker 会复用坏层。
3. **宿主磁盘满 = VM 必死**：成像前先看宿主剩余空间，至少留「镜像体积 ×1.5」。本次就因 E 盘只剩 10 GB 而 copy 到 7.4 GB 时写爆。

### 13.3 恢复后的状态（已验收）

- 14/14 容器 healthy；13 个端口全部 200（Immich 401 属正常鉴权）
- 根盘 14 G 已用 / **7.7 G 可用**；swap 正常
- 纯净性复查：普通用户 0、Samba 账户 0、Samba 共享 0、sudo 组空
- 凭据实测：OpenList `admin/NasAdmin2026!` 登录成功、workbuddy `admin/NasAdmin2026!` 登录成功

---

## 14. 二次适配与重打包记录（2026-10-30）

> 这一节记录按「删除旧镜像 → 两项适配 → 重新打包 → 压缩体积」这一轮做的工作，最终成品即 §9.1 的 `omv-nas.img.zst`。

### 14.1 两项适配

| 适配 | 做法 | 验证 |
|---|---|---|
| **网卡名自动识别** | 首启脚本新增第 3 步：扫 `/sys/class/net` 取第一块物理网卡（排除 `lo/docker0/br-/veth/virbr/tailscale/tun/tap/bond`），与 `interfaces` 不符就重写并 `systemctl restart networking`，旧文件备份 `interfaces.bak` | 脚本 `bash -n` 通过；手动跑一次，日志 `auto-discover … 本机 192.168.99.17`，网卡已匹配时正确跳过不改写 |
| **UEFI 引导支持** | 把原 1.3 GB 的 swap 区（扩展分区 `sde5`）改为 **400 MB ESP（FAT32）+ 908 MB 新 swap**，`wipefs` 清旧签名 → `apt install dosfstools grub-efi-amd64 grub-efi-amd64-signed shim-signed` → `grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=debian --no-nvram --uefi-secure-boot` → 再把 `shimx64/grubx64/mmx64` 复制成兜底路径 `\EFI\BOOT\BOOTX64.EFI` | 虚拟机切 `firmware = "efi"` 实机启动：`/sys/firmware/efi` 存在、`efi: EFI v2.4 by VMware`、NVRAM 出现 Boot0000~0002、ESP 正常挂载 |
| （附带）BIOS 仍可用 | `sfdisk` 改表后 MBR 引导代码被清，重装 `grub-install --target=i386-pc --recheck /dev/sdX` | 切回 `firmware = "bios"` 实测启动成功，14 容器正常 |

### 14.2 体积压缩做的事

1. **删内容**：`docker image prune -a -f` 回收 1.48 GB（未使用的 nyanmisaka/jellyfin、重复的 openlist 两个 tag、rclone），`apt-get clean` + 清 `/var/lib/apt/lists` 释放 0.5 GB → 根盘 14 G → **12 G**
2. **清残留**：`rm -rf /tmp/*`、journal 压到 8 MB、容器日志截断、删 `.bash_history`
3. **空闲区清零**：`dd if=/dev/zero of=/zero.fill bs=64M` 写满 10,910 MB 后删除 → 镜像里空闲区全是零，压缩比大幅提升，且不残留已删数据
4. **换压缩算法**：`gzip -1` → **`zstd -12 -T2`**（基准见 §10 最后一行）
5. **不落中间文件**：`dd | zstd` 直接经 SSH 流到 Windows（`E:\…\image_stream.py`），NAS 上不产生 7 GB 临时文件，宿主 E 盘（仅剩 5.18 GB）不受影响

### 14.3 成品与验收

| 项 | 旧版 | 新版 |
|---|---|---|
| 文件 | `omv-nas.img.gz` | **`omv-nas.img.zst`** |
| 体积 | 7,422,867,198 字节（6.91 GiB） | **4,241,872,599 字节（3.95 GiB）** |
| 压缩耗时/传输 | — | 752 秒，平均 5.4 MB/s |
| 引导 | 仅 Legacy BIOS | **UEFI + Legacy BIOS** |
| 网卡 | 写死 `ens33` | **自动识别** |
| 校验 | `gzip -t` | 流式解压：还原 **25,769,803,776 字节**（逐字节相符）+ zstd 帧校验和通过 |

- 传输完成后 NAS 已恢复：**14/14 容器 running/healthy**，`80/3000/8088/8096/2283` 端口全部开放，无不健康容器
- 首启标记已在本机重建（`.firstboot-done`），**成品镜像里没有该文件**

### 14.4 这一轮新踩的三个坑

1. **`fsfreeze` 会让长时传输卡死**：第一次取像用「冻结 + 流式」，跑到 23 分钟 / 6.5 GB 时彻底停住，之后连 SSH 登录都被 PAM 挂住，只能重启 VM。第二次改成「停 docker + sync + 不冻结」，一次跑完 ✅
2. **VMware 关机重写 vmx**：`firmware = "efi"` 在 VM 运行中改会被关机动作覆盖，白折腾一轮。必须在 `vmware-vmx` 进程退出后再改
3. **首启脚本的 `chage -d 0` 会反复咬人**：每次重启触发首启 → root 密码过期 → 自动化登录被卡，得走 `omvrescue.py` 的中转密码流程。所以「本机自用」和「分发」要分开对待：本机保留标记，交付前删标记

### 14.5 分发方式与本机解压实测

**`.zst` 用什么打开**：7-Zip **21.02 及以上**（7-Zip 自 21.02 起支持 zstd）、官方 `zstd -d`，或 **360压缩**——实测本机 360压缩 4.0 自带的 7z 内核是 `7z.dll 24.9.10.0`，属于新版 7-Zip 内核，**可以直接右键解压 `.zst`**。WinRAR 不支持 zstd，不要用它。

**本机放不下 24 GB 的问题**：C 7.3 GB / D 16.8 GB / E 5.2 GB，三个盘都装不下解压后的 24 GiB `.img`。解决办法是**稀疏解压**——`.img` 的逻辑大小仍是 24 GiB（Rufus 识别无误），但 NTFS 上只占非零区块：

| 做法 | 效果 |
|---|---|
| 4 MB 粒度跳零 | 只省 7.8 GB（ext4 元数据与空闲区交错，大量「半零」区块被迫整块写入）→ 物理 16.2 GB，仍放不下 |
| **64 KB 粒度跳零（最终采用）** | **物理 13.60 GB**，165 秒完成，D 盘够用 |

镜像内零字节占 59.6%、但完整全零的 4 MB 区块只有 32.3%，所以粒度必须细到 64 KB 才有意义。脚本：`D:\NAS-分发\解压稀疏.py`（Python + `zstandard` + `FSCTL_SET_SPARSE`）。

**校验**：稀疏 img 回读 24 GiB 全量 SHA256 = `6c03eb7f…0874`，与源盘逐字节一致 ✅

> ⚠️ **稀疏 img 只能在本机原地交给 Rufus**。一旦复制到 U 盘、exFAT 盘或网盘，空洞会被实体化，文件立刻膨胀成 24 GB。分发只发 `.zst`。

**分发渠道**：① 移动硬盘/U 盘直接拷 `.zst`（3.95 GB）+ `tools/`；② 网盘（部分免费账号单文件限 4 GB 以内，必要时拆两个分卷，对方 `copy /b 分卷一+分卷二 omv-nas.img.zst` 合并）；③ 局域网共享。成品包目录为 `D:\NAS-分发`，内含 `使用说明.txt`、`omv-nas.img`（可直接写盘）、`omv-nas.img.zst`（用于分发）、`tools\zstd.exe`（免安装）、`NAS-交接文档.md`。

---

*本文档随镜像 `omv-nas.img.zst` 一同分发。机器相关的信息（IP、SSH 主机密钥、machine-id、网卡名）由首启脚本自动重新生成；镜像内不含数据盘，也不含 `/var/lib/nas/.firstboot-done` 标记。*

---

## 15. 阿里云 ACR 分发（2026-10-30）

> 把分发包做成了 Docker 镜像推到阿里云容器镜像服务，便于对方一条命令拉取。

### 15.1 仓库信息

| 项 | 值 |
|---|---|
| 仓库地址 | `crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com/podman_images_dev/omv_images` |
| 命名空间 | `podman_images_dev` |
| 仓库名 | `omv_images` |
| 标签 | `v1`、`latest` |
| manifest 摘要 | `sha256:3e4f6c580faa1c073aa6c868b8fe8cc73a28ffefe5b7821852b9066a49f36ddf` |
| 大小 | 3.94 GB，9 层（1 层文档工具 + 8 层镜像分卷） |
| 登录用户 | `白星烁`（ACR 固定密码：`AlexMing!`） |
| 可见性 | **私有**——推送自动建仓，默认私有，需在控制台改成「公开」 |

### 15.2 对方怎么拉

```
docker login crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com -u 白星烁
docker pull crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com/podman_images_dev/omv_images:v1
docker create --name omvimg crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com/podman_images_dev/omv_images:v1
docker cp omvimg:/dist ./omv-dist
docker rm omvimg
```

`./omv-dist` 里是 `omv-nas.img.zst.part01…part08` + 文档 + 工具，先合并再解压：

```
copy /b omv-nas.img.zst.part01+...+omv-nas.img.zst.part08 omv-nas.img.zst
certutil -hashfile omv-nas.img.zst SHA256   # 应为 2a799d76…3a1b6
```

### 15.3 为什么拆成 8 个分卷

ACR **个人版对单个上传会话有累计流量限速**，实测同一会话内：64 MB 时 5.2 MB/s → 256 MB 时 1.8 MB/s → 576 MB 时 1.08 MB/s，还会继续掉。3.94 GB 走单会话要数小时。

方案：把 `omv-nas.img.zst` 按字节切成 8 个约 506 MB 的分卷，每卷一个独立层、一个独立上传会话，**4 线程并行**。每卷速率约 1.2 MB/s，4 路并行约 4.8 MB/s，总耗时 **858 秒**。分卷合并后与原文件逐字节一致，SHA256 不变。

### 15.4 这一轮踩的坑

| 现象 | 原因 | 解法 |
|---|---|---|
| 登录后 `access=[]`、推什么都 401 | **命名空间写错**（先用 `omv_images` 试）。ACR 的授权按 `命名空间/仓库` 授予，命名空间不存在就什么都不给 | 命名空间是 `podman_images_dev`，仓库名才是 `omv_images` |
| 错误密码也返回 200 + token | `dockerauth` 鉴权失败时**静默返回匿名 token**（`access=[]`），不报 401 | 看 token 里的 `access` 字段判断有没有权限，别只看 HTTP 200 |
| `requests` 报 `UnicodeEncodeError: 'latin-1'` | `HTTPBasicAuth` 把用户名按 latin-1 编码，中文用户名（白星烁）过不去 | 手工拼 `Authorization: Basic base64(utf8 用户名:密码)` |
| 上传中途 `401` 断掉 | ACR token 有效期只有 **300 秒** | 每次请求前检查剩余时间，到期前 90 秒自动刷新 |
| 上传报 `BLOB_TYPE_INVALID` / 连接被断 | **阿里云会校验 blob 内容**：拿随机字节做测试会被判非法层（`403`）；`requests` 遇到这种响应常表现为 `SSLEOFError` 而不是 403 | 测试必须用合法 gzip 数据（`\x1f\x8b` 开头） |
| 上传速度从 4 MB/s 一路掉到 0.04 MB/s | **两个原因叠加**：① 单会话累计限速（见 §15.3）；② 我第一版把 tarfile 的 10 KB 写块直接当 PATCH 体发，4 GB 变成 40 万次微请求 | 上传前缓冲成 4 MB 整块；再拆多会话并行 |
| 想用 podman 推（本机已装 5.6.0） | podman machine 的 vhdx 在 C 盘，C 只剩 7.1 GB，构建层 + 推送缓存要 ~8 GB，会把系统盘撑爆 | 放弃 podman，改用纯 Python 直连 Registry v2 API，**不落任何本地临时文件**，流式读源文件直接上传 |

---

## 16. GitHub 分发（2026-10-31）

> 同一份分发包另外发布到 GitHub，仓库公开，镜像本体走 Release 附件。

### 16.1 地址

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/1314ysys/omv_image_user_version （**Public**） |
| Release | https://github.com/1314ysys/omv_image_user_version/releases/tag/v1 |
| 账号 | `1314ysys`（git 邮箱 1240855768@qq.com，gh CLI 已登录，scopes: repo） |
| 仓库内容 | README / NAS-交接文档.md / 使用说明.txt / 分卷合并说明.txt / SHA256SUMS.txt / tools/zstd.exe / 解压稀疏.py（合计约 2 MB） |
| 附件 | `omv-nas.img.zst.part01…08`，各 505.7 MB，合计 3.95 GiB |

### 16.2 关于「能不能分卷放进 git 仓库」

结论：**不建议，正确做法是放 Release 附件**。

| 方案 | 可行性 | 问题 |
|---|---|---|
| 整个 3.95 GB 直接 commit | ❌ | GitHub 对 git 单文件 **100 MB 硬限制**，超过直接拒绝推送 |
| 切 <100 MB 分片进仓库 | ⚠️ 技术上能 | 要 43 片；仓库膨胀到 ~4 GB，远超 GitHub 建议的 1 GB，clone 极慢，且逼近 5 GB 上限，一旦历史里留了大文件就永久拖累仓库 |
| Git LFS | ❌ | 免费额度只有 **1 GB 存储 / 1 GB 流量**，装不下 3.95 GB（需买 data pack） |
| **Release 附件** | ✅ | 单附件上限 **2 GiB**，专门用来发大文件；不受 git 历史膨胀影响，还能单独重传、看下载计数 |
| 阿里云 ACR 镜像 | ✅ | 已在用（见 §15），单会话限速，需拆多会话并行 |

所以最终采用：**仓库只放文档和工具（2 MB），3.95 GB 拆 8 卷放 Release**。8 卷每卷 505.7 MB，既在 2 GiB 限制内，又与 ACR 镜像里的分卷**完全同一切法**（同一偏移、同一字节），两条分发渠道的校验值可以互相印证。

### 16.3 上传方式与实测

用 `http.client` 直连 `uploads.github.com`，显式 `Content-Length` 流式 POST（不走 chunked，不落本地临时文件 —— D 盘只剩 3.2 GB，装不下 3.95 GB 的副本）。

| 指标 | 数值 |
|---|---|
| 单卷耗时 | 56～75 秒（505.7 MB） |
| 单线程上传速率 | **6.8～9.0 MB/s**（峰值 11 MB/s） |
| 8 卷总耗时 | 约 **8.5 分钟** |
| 下载速率（单线程直连） | 约 **7.8 MB/s**，落在 `release-assets.githubusercontent.com` |

对比 ACR（§15.3）：GitHub 单连接就稳定 7～9 MB/s，ACR 单会话 1.2 MB/s 且越传越慢。**同一份 3.95 GB，GitHub 用 8.5 分钟，ACR 用 14 分钟（还是靠 4 路并行），单会话直传更是要数小时。**

### 16.4 校验结果

GitHub 会为每个附件计算 SHA256 并在 API 的 `digest` 字段返回，直接与本地 `SHA256SUMS.txt` 比对，8 卷**全部一致**（无需下载回来验证）：

`
part01 c38c09300b5c57fb…   part05 561fc3cc9eb4d2d3…
part02 e7a146e26c70c57b…   part06 81872716a7507d99…
part03 dcd5596322fcdc47…   part07 b6fc1e60ae1245ec…
part04 4bc6aac60d7f9016…   part08 f8502feff077da91…
合并后 2a799d76d8dcb57a38d8783856d39df92bffb625fcc6dd5edd27905a8133a1b6
`

另外做了 Range 限长下载测试：`HTTP 206`，取回的前 1 MB 与本地文件逐字节一致。

### 16.5 复用手法（以后换版本）

```
# 1. 改版本号后重算分卷校验
python E:\Deepseek_Harness\worknet\gh_upload_parts.py

# 2. 脚本自带幂等：已存在且大小一致的附件自动跳过，失败自动删残片重传（最多 5 次）
```

脚本位置：`E:\Deepseek_Harness\worknet\gh_upload_parts.py`；仓库内容在 `E:\Deepseek_Harness\worknet\gh-omv\`。
