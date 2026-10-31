# omv_image_user_version

OMV NAS 系统盘的**可启动镜像**分发包 —— 含系统镜像、配套工具、交接文档。

- 系统：OpenMediaVault **8.6.0-1 (Synchrony)** / Debian 13 trixie / 内核 6.12
- 内容：OMV 面板 + Docker + 14 个容器（Jellyfin、Immich、OpenList、MetaTube 等）+ 首启自动化
- 引导：**MBR/Legacy BIOS 与 UEFI（含 Secure Boot）双引导**
- 镜像大小：解压后 **24 GiB**（整个系统盘，含分区表）；压缩包 **3.95 GiB**

---

## 一、怎么下载

镜像本体不放在 git 仓库里，而是放在 **[Releases → v1](https://github.com/1314ysys/omv_image_user_version/releases/tag/v1)** 的附件中，分成 8 个分卷（每卷 505.7 MB，合计 3.95 GiB）：

| 文件 | 大小 | 直链 |
|---|---|---|
| `omv-nas.img.zst.part01` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part01) |
| `omv-nas.img.zst.part02` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part02) |
| `omv-nas.img.zst.part03` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part03) |
| `omv-nas.img.zst.part04` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part04) |
| `omv-nas.img.zst.part05` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part05) |
| `omv-nas.img.zst.part06` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part06) |
| `omv-nas.img.zst.part07` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part07) |
| `omv-nas.img.zst.part08` | 505.7 MB | [下载](https://github.com/1314ysys/omv_image_user_version/releases/download/v1/omv-nas.img.zst.part08) |

实测单线程直连下载约 **7.8 MB/s**（走 GitHub 的 `release-assets.githubusercontent.com` CDN），全部 8 卷约 8～10 分钟。

> **为什么不直接放进仓库？**
> GitHub 对 git 仓库里的单个文件有 **100 MB 硬限制**（超过直接拒绝推送），LFS 免费额度只有 1 GB 存储，
> 都装不下 3.95 GB。切到 100 MB 以下要 40+ 个文件，仓库会膨胀到 4 GB，远超 GitHub 建议的 1 GB，
> clone 会非常痛苦。**Releases 附件单文件上限 2 GiB**，正是用来分发这类大文件的。

## 二、合并分卷

**Windows（命令行，在解压出来的目录里执行）**

```bat
copy /b omv-nas.img.zst.part01+omv-nas.img.zst.part02+omv-nas.img.zst.part03+omv-nas.img.zst.part04+omv-nas.img.zst.part05+omv-nas.img.zst.part06+omv-nas.img.zst.part07+omv-nas.img.zst.part08 omv-nas.img.zst
```

**Linux / macOS**

```bash
cat omv-nas.img.zst.part* > omv-nas.img.zst
```

顺序必须 `part01 → part08`，缺一不可。

## 三、校验

```bat
certutil -hashfile omv-nas.img.zst SHA256
```

期望值：`2a799d76d8dcb57a38d8783856d39df92bffb625fcc6dd5edd27905a8133a1b6`

各分卷的独立校验值见 [`SHA256SUMS.txt`](SHA256SUMS.txt)。

## 四、解压并写入 U 盘

1. **解压**：用 7-Zip ≥21.02 或 **360压缩**（自带 7z 内核 24.9，支持 `.zst`）右键解压 → 得到 `omv-nas.img`（24 GiB，需要 24 GB 空闲空间）
   - 空间不足时用 [`解压稀疏.py`](解压稀疏.py)：跳过全零区块，只占约 13.6 GB，生成的文件同样可以给 Rufus 用（逻辑大小仍是 24 GiB）
2. **写盘**：Rufus → 选择 `omv-nas.img` → 分区类型 **MBR** → 开始 → 弹窗选 **「以 DD 镜像模式写入」**
3. 目标 U 盘 **≥32 GB**（镜像 24 GiB）

## 五、首次开机

镜像不含数据盘，也不含首启标记，所以第一次开机会自动完成：

```
重生成 machine-id 与 SSH 主机密钥
→ 自动识别网卡名并重写 /etc/network/interfaces（换机器网卡叫 enp3s0/eno1 也能拿到 IP）
→ 强制修改 root 密码
→ 把配置里写死的旧 IP 换成当前 IP
→ 自动拉起全部 14 个容器
```

控制台会显示当前 IP。默认凭据：

| 入口 | 账号 | 密码 |
|---|---|---|
| 控制台 / SSH | `root` | `NasAdmin2026!`（首启强制修改） |
| OMV 面板 `/` | `admin` | `NasAdmin2026!` |
| OpenList `:5244` | `admin` | `NasAdmin2026!` |

之后需自己接数据盘 → 建文件系统 → 建 mergerfs 池 → 配 SnapRAID（详见 `NAS-交接文档.md` §9.4）。

## 六、仓库内容

| 文件 | 说明 |
|---|---|
| `NAS-交接文档.md` | 完整交接文档：功能来源、存储栈、服务清单、凭据、自动化、已知坑、运维手册 |
| `使用说明.txt` | 分发 / 写盘 / 首启的简明说明 |
| `分卷合并说明.txt` | 分卷合并命令与校验 |
| `SHA256SUMS.txt` | 全部分卷与合并后文件的校验值 |
| `tools/zstd.exe` | 免安装 zstd（Windows 64 位），用于解压 `.zst` |
| `解压稀疏.py` | 空间不足 24 GB 时的稀疏解压脚本（需 Python + `zstandard`） |

## 七、同一份内容也在阿里云 ACR

```bash
docker login crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com -u <用户名>
docker pull crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com/podman_images_dev/omv_images:v1
docker create --name omvimg crpi-muahgwhixaz856an.cn-hangzhou.personal.cr.aliyuncs.com/podman_images_dev/omv_images:v1
docker cp omvimg:/dist ./omv-dist
docker rm omvimg
```

`./omv-dist` 里是同样的 8 个分卷，合并方式与上面一致。

---

## 注意事项

- 镜像里**只有系统盘**，数据盘（mergerfs 池 / SnapRAID 校验盘）需要目标机自己准备
- 系统盘设备名每次开机可能变化（`sda`/`sdc`/`sde` 都出现过），但 `/etc/fstab`、mergerfs、SnapRAID 全部按 **UUID** 引用，不影响启动
- 稀疏 img 只能在本机原地交给 Rufus；一旦复制到 U 盘 / exFAT / 网盘，空洞会实体化，文件立刻膨胀成 24 GB
