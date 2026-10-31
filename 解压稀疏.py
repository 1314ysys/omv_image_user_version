# -*- coding: utf-8 -*-
"""把 omv-nas.img.zst 解压成稀疏 img：逻辑 24 GiB，物理只占非零区块。
仅在目标盘放不下 24 GB 时使用；空间充足时直接解压更快。"""
import ctypes
import msvcrt
import os
import sys
import time

import zstandard

FSCTL_SET_SPARSE = 0x000900C4
BLK = 65536          # 64KB 判定粒度
BUF = 16 * 1024 * 1024
EXPECT = 25769803776

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE).lower() == 'tools' else HERE
SRC = os.path.join(ROOT, 'omv-nas.img.zst')
DST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'omv-nas.img')


def free_gb(path):
    drive = os.path.splitdrive(os.path.abspath(path))[0] + '\\'
    free = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, None, ctypes.byref(free))
    return free.value / 1073741824.0


def main():
    print('源文件  : %s' % SRC)
    print('目标    : %s' % DST)
    f0 = free_gb(DST)
    print('起始空闲: %.2f GB' % f0)
    sys.stdout.flush()

    fh = open(DST, 'wb')
    handle = msvcrt.get_osfhandle(fh.fileno())
    ret = ctypes.c_uint32(0)
    ok = ctypes.windll.kernel32.DeviceIoControl(
        ctypes.c_void_p(handle), FSCTL_SET_SPARSE, None, 0, None, 0, ctypes.byref(ret), None)
    print('稀疏属性: %s' % ('已启用' if ok else '启用失败（将完整写入）'))
    sys.stdout.flush()

    d = zstandard.ZstdDecompressor()
    pos = 0
    written = 0
    t0 = time.time()
    last = t0
    with open(SRC, 'rb') as src, d.stream_reader(src) as r:
        while True:
            buf = r.read(BUF)
            if not buf:
                break
            n = len(buf)
            for off in range(0, n, BLK):
                blk = buf[off:off + BLK]
                if blk.count(0) != len(blk):
                    fh.seek(pos + off)
                    fh.write(blk)
                    written += len(blk)
            pos += n
            now = time.time()
            if now - last >= 5:
                last = now
                print('  解压 %5.1f/24.0 GB  实写 %5.2f GB  空闲 %5.2f GB  %4.0f MB/s'
                      % (pos / 1073741824.0, written / 1073741824.0, free_gb(DST), pos / 1048576.0 / (now - t0)))
                sys.stdout.flush()
                if free_gb(DST) < 1.0:
                    print('  剩余空间不足 1 GB，中止')
                    break
    fh.truncate(pos)
    fh.close()

    f1 = free_gb(DST)
    print('')
    print('========== 结果 ==========')
    print('逻辑大小: %d 字节 (%.2f GiB)' % (pos, pos / 1073741824.0))
    print('期望大小: %d 字节  -> %s' % (EXPECT, '一致' if pos == EXPECT else '不一致'))
    print('实际占用: %.2f GB' % (f0 - f1))
    print('耗时    : %.0f 秒' % (time.time() - t0))
    print('=========================')
    return 0 if pos == EXPECT else 1


if __name__ == '__main__':
    sys.exit(main())
