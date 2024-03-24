import os
import re
import time
import subprocess

APK_DIR = 'samples'  # 样本存放目录
AAPT_PATH = 'D:\\Android\\android-sdk\\build-tools\\30.0.1\\aapt'  # 修改为你的 aapt 路径

# 对于安装了 EdXposed 的设备
XPOSED_LOG_FILE = '/data/user_de/0/org.meowcat.edxposed.manager/log/all.log'
# 对于安装了原始 Xposed 的设备
# XPOSED_LOG_FILE = '/data/data/de.robv.android.xposed.installer/log/error.log'

LOG_DIR = 'log'  # 日志存放目录
RUN_TIME = 60  # 运行时间（秒）

if __name__ == "__main__":
    apk_list = os.listdir(APK_DIR)
    count = 0
    subprocess.run(['adb', 'root'])  # 获取 root 权限
    for apk in apk_list:
        count += 1
        if (apk + '.log') in os.listdir(LOG_DIR):
            print('%d: %s 已经分析过.' % (count, apk))
            continue

        # 获取 APK 文件的包名
        pkg_name_raw = subprocess.run([AAPT_PATH, 'dump', 'badging', os.path.join(APK_DIR, apk)], capture_output=True, text=True).stdout
        match = re.search("name=\'[a-zA-Z0-9._]*\'", pkg_name_raw)
        if match is None:
            print('未找到包名')
            continue
        l = match.span()
        pkg_name = pkg_name_raw[l[0] + 6: l[1] - 1]

        # 在 /sdcard 上设置 PackageName 文件
        subprocess.run(['adb', 'shell', 'rm', '/sdcard/PackageName'])
        subprocess.run(['adb', 'shell', 'echo ' + pkg_name + ' > /sdcard/PackageName'])

        # 重启设备
        subprocess.run(['adb', 'shell', 'reboot', 'now'])
        while True:
            result = subprocess.run(['adb', 'shell', 'getprop', 'sys.boot_completed'], capture_output=True, text=True).stdout
            if result.strip() == '1':
                break
            else:
                time.sleep(3)
        time.sleep(5)
        subprocess.run(['adb', 'shell', 'settings', 'put', 'global', 'airplane_mode_on', '0'])  # 关闭飞行模式
        subprocess.run(['adb', 'shell', 'svc', 'wifi', 'enable'])  # 启用 Wi-Fi

        # 安装 APK 到设备
        result = subprocess.run(['adb', 'install', os.path.join(APK_DIR, apk)], capture_output=True, text=True)
        if 'Failure' in result.stdout:
            with open(os.path.join(LOG_DIR, 'failure_apk.log'), 'a') as f:
                f.write(pkg_name + ': ' + result.stdout[result.stdout.find('Failure'):])
            continue
        time.sleep(5)

        # 授予权限
        pkg_perm_raw = subprocess.run([AAPT_PATH, 'dump', 'badging', os.path.join(APK_DIR, apk)], capture_output=True, text=True).stdout
        pkg_perm = re.finditer(r"android.permission.[A-Z_]+", pkg_perm_raw)
        for perm in pkg_perm:
            subprocess.run(['adb', 'shell', 'pm', 'grant', pkg_name, perm.group()])
        time.sleep(3)

        # 开始监视
        start_time = time.time()
        while True:
            subprocess.run(['adb', 'shell', 'monkey', '-p', pkg_name, '--throttle', '300', '--ignore-crashes', '--ignore-timeouts', '--monitor-native-crashes', '100'])
            if RUN_TIME < (time.time() - start_time):
                break

        # 停止应用
        subprocess.run(['adb', 'shell', 'am', 'force-stop', pkg_name])

        # 卸载应用
        subprocess.run(['adb', 'uninstall', pkg_name])

        # 获取 xposed 日志
        subprocess.run(['adb', 'pull', XPOSED_LOG_FILE, os.path.join(LOG_DIR, apk + '.log')])

        # 删除旧的 xposed 日志
        subprocess.run(['adb', 'shell', 'rm', XPOSED_LOG_FILE])

        # 完成
        print(str(count) + ': 文件 ' + apk + ' 处理完毕.')
