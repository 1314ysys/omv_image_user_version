# OMV NAS 系统盘镜像（v2 净化版）

一块「开箱即用」的 NAS 系统盘镜像：**OpenMediaVault 8.6 + Docker + 14 个容器 + 首启自动化**，
MBR 引导（Legacy BIOS / UEFI 含 Secure Boot 均可），目标盘 ≥ 24 GiB。

- 当前版本：**v2**（2026-10-31）—— 账号残留彻底清零，正常关机取像（ext4 clean）
- 下载：[Releases → v2](https://github.com/1314ysys/omv_image_user_version/releases/tag/v2)
- 阿里云 ACR：`crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com/podman_images_dev/omv_images:v2`
- 完整说明见 [`NAS-交接文档.md`](NAS-交接文档.md)（§17 是 v2 的净化记录）

## 一、镜像里有什么

| 类别 | 内容 |
|---|---|
| 系统 | Debian 13 (trixie)，内核 6.12，OpenMediaVault 8.6.0-1 |
| 存储 | mergerfs 合并池 `/srv/mergerfs/pool` + SnapRAID（数据盘需自己建） |
| 容器 | Jellyfin、Immich（server / ML / postgres / redis）、qBittorrent、Homepage、Nginx Proxy Manager、OpenList、MetaTube、frpc、opencode / qoder / freellm / workbuddy 等 14 个 |
| 面板 | OMV WebUI `http://<IP>/`、导航页 `http://<IP>:3000/` |
| 首启 | `nas-firstboot.sh` 自动重置 machine-id / SSH 主机密钥 / 网卡配置，强制 root 改密 |

默认账号：`root` / `admin`，初始密码 `NasAdmin2026!`；**root 首次登录强制改密**。

## 二、尺寸与校验

| 项目 | 值 |
|---|---|
| 原始镜像 | `omv-nas.img` 25,769,803,776 字节（24.00 GiB） |
| 原始镜像 SHA256 | `552485f92676c5346824edba4e6d5bc4105dbccf55c925cefe735973966f054e` |
| 压缩包 | `omv-nas.img.zst` 4,090,902,949 字节（3.810 GB） |
| 压缩包 SHA256 | `a12ea9733aa2cdc39dbb5922c2d72b6e11dba083b5ed7e0797bbdb421a9b753f` |
| 分卷 | `part01`–`part08`，每卷 487.7 MB |

## 三、怎么用

```bat
:: 1. 合并 8 个分卷（顺序不能错，一卷不能缺）
copy /b omv-nas.img.zst.part01+omv-nas.img.zst.part02+omv-nas.img.zst.part03+omv-nas.img.zst.part04+omv-nas.img.zst.part05+omv-nas.img.zst.part06+omv-nas.img.zst.part07+omv-nas.img.zst.part08 omv-nas.img.zst

:: 2. 校验（应等于 a12ea973…a9b753f）
certutil -hashfile omv-nas.img.zst SHA256

:: 3. 解压成 24 GiB 镜像（空间不够 24 GB 时用 解压稀疏.py）
tools\zstd.exe -d omv-nas.img.zst
```

然后 Rufus 写盘：「选择」`omv-nas.img` → 分区类型 **MBR** → 开始 → 弹窗选 **以 DD 镜像模式写入**。

首次开机约 15 秒完成首启初始化，控制台会打印当前 IP、默认密码和后续三步。

## 四、首启后必做的三件事

1. 默认地址 `192.168.99.17`，去 OMV 面板改成你自己网段的固定 IP（`ip -br link` 查网卡名）
2. 改掉默认密码（root 会强制改，admin 请自己改）
3. 本镜像只含系统盘：存储盘需自己建文件系统 → 做 mergerfs 合并池 → 加 SnapRAID

## 五、v2 相比 v1 改了什么

v1 只删了账号本体，v2 把残留也清了：

- `/etc/passwd-`、`/etc/group-`、`/etc/gshadow-`、`/etc/subuid-`、`/etc/subgid-`（删除账号时自动留的备份）
- `/etc/openmediavault/config.xml` 里 3 段残留 `<privilege>`
- Samba 账号库 `passdb.tdb` / `secrets.tdb`
- 登录与系统日志：`wtmp` / `wtmpdb` / `btmp` / `lastlog` / `systemd journal`
- swap 分区整块清零重建（**UUID 不变**，`/etc/fstab` 照常）
- 文件系统空闲块两轮 dd 填零（约 22.8 GB）
- 取像改为**正常关机**，ext4 处于 clean 状态，首启不需要日志重放

整盘字符串扫描后，`nasuser` 只剩 2 处，都是系统自带 `/usr/bin/cvtsudoers` 的选项名
`runasusers`（误报）；`getent passwd` / `/etc/shadow` / `/etc/group` / `config.xml` 命中数为 0。
真机启动实测：15 秒进 SSH、14 个容器自动全起、OMV + nginx + php-fpm 全 active。

## 六、文件

| 文件 | 说明 |
|---|---|
| `NAS-交接文档.md` | 完整交接文档：组件来源、存储栈、服务清单、凭据、运维、踩过的坑、v2 净化记录 |
| `使用说明.txt` | 写盘 / 首启 / 分发说明 |
| `分卷合并说明.txt` | 分卷合并与校验 |
| `SHA256SUMS.txt` | 整卷 + 每卷校验值 |
| `解压稀疏.py` | 空间不足 24 GB 时的稀疏解压脚本（需 Python + zstandard） |

## 七、注意

- `omv-nas.img` 是**稀疏文件**，只适合本机原地交给 Rufus；拷到 U 盘 / 网盘 / exFAT 会立刻膨胀成 24 GB
- 分发只给 `.zst` 及分卷，不给 `.img`
- 数据盘内容不在镜像里；镜像里的 mergerfs / SnapRAID 只有配置，盘要自己加
- `minidlna` 与 `systemd-networkd-wait-online` 两个单元在 `systemctl --failed` 里显示失败，
  属 OMV 用 ifupdown 管理网络的正常现象 / DLNA 无媒体目录，与功能无关
