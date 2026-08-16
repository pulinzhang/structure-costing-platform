# 将离线安装包放在此目录（可选）
#
# 1) Python 安装包（文件名需匹配 python-3.12*-amd64.exe）
#    例: python-3.12.8-amd64.exe
#
# 2) 依赖 wheels（子目录 wheels\）
#    在有网机器执行:
#      pip download -r requirements.txt -d scripts/windows/vendor/wheels
#
# 3) NSSM（注册 Windows 服务用）
#    解压后放置: nssm\win64\nssm.exe
#    下载: https://nssm.cc/download
#
# 详见 docs/deploy-windows-production.md
