import os
import shutil
import subprocess
import random
import socket
from pathlib import Path
from datetime import datetime, timedelta
import sys
import time
import json
import time
import requests
from urllib.parse import urlparse
import bashshim.turnstile_test as turnstile_test

class BashShim:
    def __init__(self, fallback='error', os_flavor="Linux", kernel_version="5.15.0-fake", username="aurahack", uid=1337, distro_name="FakeOS", distro_codename="marie", distro_id="fakeos", distro_version="1.0", package_manager="apt", package_manager_mirror="http://package.fakeos.org", log_dmesg=True, allow_networking=True):
        self.distro_name = distro_name
        self.distro_codename = distro_codename
        self.distro_id = distro_id
        self.distro_version = distro_version
        self.package_manager = package_manager
        self.package_manager_mirror = package_manager_mirror
        self.fallback = fallback.lower()
        self.sim_os = os_flavor if os_flavor else random.choice(['Linux'])
        self.username = username
        self.uid = uid
        self.is_root = False  # toggled by sudo
        self.hostname = socket.gethostname()
        self.log_dmesg = log_dmesg
        self.allow_networking = allow_networking
        self.kernel_version = kernel_version
        self.session_start = time.time()

        self.home = Path.home()
        self.fakeroot = self.home / 'fakeroot'
        self.cwd = self.fakeroot
        self._log(f"bashshim: initializing BashShim for user '{username}' on simulated OS '{self.sim_os}' (host: {self.hostname})")
        self.simulated = {
            'echo': self.cmd_echo,
            'pwd': self.cmd_pwd,
            'ls': self.cmd_ls,
            'cd': self.cmd_cd,
            'cat': self.cmd_cat,
            'uname': self.cmd_uname,
            'whoami': self.cmd_whoami,
            'sudo': self.cmd_sudo,
            'touch': self.cmd_touch,
            'ps': self.cmd_ps,
            'true': lambda args: (0, ''),
            'false': lambda args: (1, ''),
            self.package_manager: self.cmd_pkg_manager,
            'python3': self.cmd_python3,
            'hostname': self.cmd_hostname,
            'uptime': self.cmd_uptime,
            'rm': self.cmd_rm,
            'mkdir': self.cmd_mkdir,
            'rmdir': self.cmd_rmdir,
            'head': self.cmd_head,
            'tail': self.cmd_tail,
            'stat': self.cmd_stat,
            'grep': self.cmd_grep,
            'sleep': self.cmd_sleep,
            'read': self.cmd_read,
            'kill': self.cmd_kill,
            'id': self.cmd_id,
            'passwd': self.cmd_passwd,
            'dmesg': self.cmd_dmesg,
            'free': self.cmd_free,
            'curl': self.cmd_curl,
            'rebuildfs': self.cmd_rebuildfs,
        }
        
        self._init_fakeroot()
        self._create_proc()
        self._log("bashshim: startup complete")


    def _log(self, msg):
        now = datetime.now().strftime('%b %d %H:%M:%S')
        if not hasattr(self, '_log_buffer'):
            self._log_buffer = []
        log_entry = f"[{now}] {msg}"
        self._log_buffer.append(log_entry)
        if self.log_dmesg:
            print(f"[dmesg] {now} {msg}", file=sys.stderr)
        try:
            with open(self.fakeroot / 'bashshim.log', 'a') as log_file:
                log_file.write(log_entry + "\n")
        except Exception as e:
            pass # Probably an attempt to log before we have that file, ignore it as the buffer logs it anyway

    def _init_fakeroot(self):
        self._log(f"bashshim: checking fakeroot at {self.fakeroot}")
        if not self.fakeroot.exists():
            self.fakeroot.mkdir()
            self._log(f"bashshim: created fakeroot directory at {self.fakeroot}")
        # Ignore bashshim.log when checking if fakeroot is empty
        entries = [p for p in self.fakeroot.iterdir() if p.name != "bashshim.log"]
        if not entries:
            self._log("bashshim: fakeroot is empty, populating structure")
            self._populate_structure()
        else:
            self._log("bashshim: fakeroot already populated")
    def _populate_structure(self):
        import shutil

        # Define UID/GID per OS
        uid = self.uid
        gid = 1000
        if self.sim_os == 'Darwin':
            uid = 501
            gid = 20
        elif self.sim_os == 'BSD':
            uid = 1001
            gid = 1001

        structure = {
            'Linux': {
                'bin': [],
                'sbin': [
                    'init', 'reboot', 'shutdown', 'halt', 'fsck', 'mount', 'umount', 'ifconfig', 'sysctl'
                ],
                'etc': {
                    'passwd': (
                        f"root:x:0:0:root:/root:/bin/bash\n"
                        f"{self.username}:x:{uid}:{gid}:{self.username}:/home/{self.username}:/bin/bash\n"
                    ),
                    'shadow': (
                        f"root:*:19376:0:99999:7:::\n"
                        f"{self.username}:*:19376:0:99999:7:::\n"
                    ),
                    'group': (
                        f"root:x:0:\n"
                        f"{self.username}:x:{gid}:{self.username}\n"
                    ),
                    'hosts': "127.0.0.1\tlocalhost\n::1\tlocalhost\n",
                    'hostname': f"{self.hostname}\n",
                    'resolv.conf': "nameserver 8.8.8.8\n",
                    'issue': f"Welcome to {self.distro_name} {self.distro_version} (simulated)\n",
                    'os-release': (
                        f'NAME="{self.distro_name}"\n'
                        f'ID={self.distro_id}\n'
                        f'VERSION="{self.distro_version}"\n'
                        f'PRETTY_NAME="{self.distro_name} {self.distro_version}"\n'
                    ),
                    'fstab': (
                        "proc /proc proc defaults 0 0\n"
                        "/dev/sda1 / ext4 defaults 0 1\n"
                    ),
                    'motd': "Welcome to FakeOS!\n",
                    'profile': "# /etc/profile: system-wide .profile file for the Bourne shell\n",
                    'bash.bashrc': "# System-wide bashrc\n",
                    'localtime': "",
                },
                'etc/network': {
                    'interfaces': (
                        "auto lo\niface lo inet loopback\n"
                        "auto eth0\niface eth0 inet dhcp\n"
                    )
                },
                'usr/bin': [
                    'nano', 'python3', 'vim', self.package_manager, 'env', 'which', 'man', 'less', 'more', 'clear', 'top', 'htop', 'ssh', 'scp', 'wget', 'curl', 'tar', 'gzip', 'gunzip', 'zip', 'unzip'
                ],
                'usr/sbin': [
                    'sshd', 'useradd', 'userdel', 'groupadd', 'groupdel', 'adduser', 'deluser', 'service'
                ],
                'lib': [],
                'lib64': [],
                'home': [self.username],
                'root': [],
                'var': {
                    'log': ['syslog', 'auth.log', 'dmesg', 'kern.log', 'messages', 'boot.log'],
                    'tmp': [],
                    'run': [],
                    'lib': [],
                    'cache': [],
                    'spool': [],
                    'mail': [],
                },
                'proc': [],
                'tmp': [],
                'dev': ['null', 'zero', 'tty', 'random', 'urandom', 'sda', 'sda1', 'loop0'],
                'boot': ['vmlinuz', 'initrd.img', 'grub'],
                'media': [],
                'mnt': [],
                'srv': [],
                'opt': [],
                'run': [],
                'sys': [],
            },
                
            'Darwin': {
                'bin': [
                    'ls', 'cat', 'touch', 'ps', 'zsh', 'sh', 'bash', 'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'echo', 'pwd', 'true', 'false', 'grep', 'head', 'tail', 'chmod', 'chown', 'ln', 'sleep', 'kill', 'stat', 'uname', 'whoami', 'id', 'passwd', 'hostname', 'date', 'open'
                ],
                'sbin': [
                    'reboot', 'shutdown', 'ifconfig', 'diskutil', 'mount', 'umount', 'fsck', 'sysctl'
                ],
                'etc': {
                    'hosts': "127.0.0.1\tlocalhost\n::1\tlocalhost\n",
                    'hostname': f"{self.hostname}\n",
                    'resolv.conf': "nameserver 1.1.1.1\n",
                    'passwd': (
                        f"root:*:0:0:System Administrator:/var/root:/bin/sh\n"
                        f"{self.username}:*:501:20:{self.username}:/Users/{self.username}:/bin/zsh\n"
                    ),
                    'group': (
                        f"wheel:*:0:root\n"
                        f"staff:*:20:{self.username}\n"
                    ),
                    'profile': "# /etc/profile for macOS\n",
                    'bashrc': "# /etc/bashrc for macOS\n",
                    'localtime': "",
                    'fstab': "",
                    'motd': "Welcome to Darwin (simulated)\n",
                },
                'usr/bin': [
                    'open', 'sw_vers', 'python3', 'vim', 'nano', 'env', 'which', 'man', 'less', 'more', 'clear', 'top', 'ssh', 'scp', 'curl', 'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'osascript'
                ],
                'usr/sbin': [
                    'sshd', 'diskutil', 'systemsetup'
                ],
                'System/Library': [],
                'System/Applications': [],
                'System/Library/CoreServices': [],
                'System/Library/Frameworks': [],
                'System/Library/Extensions': [],
                'System/Library/LaunchAgents': [],
                'System/Library/LaunchDaemons': [],
                'System/Library/StartupItems': [],
                'System/Library/PreferencePanes': [],
                'System/Library/PrivateFrameworks': [],
                'System/Library/Audio': [],
                'System/Library/ColorSync': [],
                'System/Library/Components': [],
                'System/Library/Contextual Menu Items': [],
                'System/Library/Frameworks': [],
                'System/Library/Input Methods': [],
                'System/Library/Internet Plug-Ins': [],
                'System/Library/PreferencePanes': [],
                'System/Library/Printers': [],
                'System/Library/Sounds': [],
                'System/Library/Spotlight': [],
                'System/Library/Widgets': [],
                'System/Library/Extensions': [],
                'System/Applications': [],
                'Applications': [],
                'Applications/Safari.app': [],
                'Applications/Utilities/Terminal.app': [],
                'Applications/Utilities/Activity Monitor.app': [],
                'Applications/Utilities/Disk Utility.app': [],
                'Applications/Utilities/Console.app': [],
                'Applications/Calculator.app': [],
                'Applications/TextEdit.app': [],
                'Applications/Preview.app': [],
                'Applications/Photos.app': [],
                'Applications/Mail.app': [],
                'Applications/Messages.app': [],
                'Applications/Calendar.app': [],
                'Applications/Notes.app': [],
                'Applications/Contacts.app': [],
                'Applications/Maps.app': [],
                'Applications/Reminders.app': [],
                'Applications/Podcasts.app': [],
                'Applications/Music.app': [],
                'Applications/TV.app': [],
                'Applications/News.app': [],
                'Applications/FaceTime.app': [],
                'Applications/Books.app': [],
                'Applications/Shortcuts.app': [],
                'Applications/Automator.app': [],
                'Applications/System Settings.app': [],
                
                'Users': [self.username],
                'Users/Shared': [],
                'Volumes': [],
                'private/tmp': [],
                'private/var': ['log', 'tmp', 'run'],
                'dev': ['null', 'zero', 'tty', 'disk0', 'disk1', 'random', 'urandom'],
                'tmp': [],
                'Library': ['Preferences', 'Logs'],
                'opt': [],
            },
            'BSD': {
                'bin': [
                    'ls', 'cat', 'touch', 'ps', 'sh', 'csh', 'tcsh', 'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'echo', 'pwd', 'true', 'false', 'grep', 'head', 'tail', 'chmod', 'chown', 'ln', 'sleep', 'kill', 'stat', 'uname', 'whoami', 'id', 'passwd', 'hostname', 'date'
                ],
                'sbin': [
                    'init', 'reboot', 'shutdown', 'halt', 'ifconfig', 'sysctl', 'mount', 'umount', 'fsck'
                ],
                'etc': {
                    'hosts': "127.0.0.1\tlocalhost\n::1\tlocalhost\n",
                    'passwd': (
                        f"root:*:0:0:Charlie Root:/root:/bin/sh\n"
                        f"{self.username}:*:1001:1001:{self.username}:/home/{self.username}:/bin/sh\n"
                    ),
                    'group': (
                        f"wheel:*:0:root\n"
                        f"{self.username}:*:1001:{self.username}\n"
                    ),
                    'rc.conf': "hostname=\"bsdhost\"\nifconfig_em0=\"DHCP\"\n",
                    'fstab': (
                        "/dev/ada0p2 / ufs rw 1 1\n"
                        "proc /proc procfs rw 0 0\n"
                    ),
                    'motd': "Welcome to BSD (simulated)\n",
                    'profile': "# /etc/profile for BSD\n",
                    'localtime': "",
                },
                'usr/bin': [
                    'csh', 'less', 'vi', 'env', 'which', 'man', 'more', 'clear', 'top', 'ssh', 'scp', 'curl', 'tar', 'gzip', 'gunzip', 'zip', 'unzip'
                ],
                'usr/sbin': [
                    'sshd', 'service', 'pw', 'adduser', 'rmuser'
                ],
                'home': [self.username],
                'root': [],
                'var': {
                    'log': ['messages', 'auth.log', 'dmesg', 'cron'],
                    'tmp': [],
                    'run': [],
                    'mail': [],
                },
                'tmp': [],
                'dev': ['null', 'zero', 'tty', 'random', 'urandom', 'ada0', 'ada0p2'],
                'boot': ['kernel', 'loader.conf'],
                'mnt': [],
                'media': [],
                'proc': [],
                'usr/local/bin': [],
                'usr/local/sbin': [],
            }
        }

        os_data = structure.get(self.sim_os, {})
        self._log(f"bashshim: populating detailed simulated filesystem for {self.sim_os}")

        for path, content in os_data.items():
            time.sleep(0.1)  # Simulate some delay for realism
            full_path = self.fakeroot / path
            full_path.mkdir(parents=True, exist_ok=True)

            if isinstance(content, list):
                for fname in content:
                    lena_quotes = [
                        "# Lena Raine's music doesn't just soundtrack games—it soundtracks healing.",
                        "# When Lena composed Celeste, she didn't just write songs. She told a story trans girls could survive by.",
                        "# Lena's melodies are like safehouses: shimmering spaces where anxious hearts can breathe.",
                        "# Lena Raine supremacy isn't just about musical skill—it's about *truth through sound.*",
                        "# 'Resurrections' still makes me cry. And I'm not sorry about it.",
                        "# Lena and Erica are proof that queer love can thrive in a world that tried to erase us.",
                        "# You can *hear* the transition arc in Lena's music. It's not subtle. It's sacred.",
                        "# The moment you hear 'Reach for the Summit' and realize it's *about you*? That's when the magic hits.",
                        "# Lena Raine didn't just break into the game industry—she rewrote the sonic palette for how we feel.",
                        "# Every single ambient track Lena makes is like: 'Hey, what if anxiety had a soft place to land?'",
                        "# Lena Raine: the composer who made thousands of queer kids realize they weren't alone.",
                        "# Her Minecraft track 'Otherside' isn't just cool. It's *trans-coded astral rebellion.*",
                        "# Erica Lahaie's art + Lena Raine's sound = the trans power couple aesthetic pipeline.",
                        "# Lena's music feels like opening a locked journal and finding a page written by your future self.",
                        "# You don't *listen* to Celeste. You *heal* to it.",
                        "# The moment you realize REDSKY is Lena's inner storm, and you survived that storm too.",
                        "# Lena Raine made video game music emotional—and made emotion the point.",
                        "# Oneknowing didn't just push ambient boundaries. It whispered: 'You're allowed to *be.*'",
                        "# If you've ever cried while speedrunning a level, you probably owe Lena Raine royalties.",
                        "# Lena writes like someone who's lived the weight of invisibility—and composed her way out."
                    ]
                    quote = random.choice(lena_quotes)
                    fpath = full_path / fname
                    fpath.write_text(f"# I <3 Lena Raine\n" if '.' not in fname else "")
                    self._log(f"bashshim: created {fpath}")
            elif isinstance(content, dict):
                for fname, fcontent in content.items():
                    fpath = full_path / fname
                    if isinstance(fcontent, str):
                        fpath.write_text(fcontent)
                        self._log(f"bashshim: created and populated {fpath}")
                    elif isinstance(fcontent, list):
                        # Create empty files for each item in the list
                        for subfname in fcontent:
                            subfpath = fpath / subfname if not (full_path / fname).is_file() else full_path / subfname
                            subfpath.parent.mkdir(parents=True, exist_ok=True)
                            subfpath.write_text("")
                            self._log(f"bashshim: created {subfpath}")
                    else:
                        # If it's not a str or list, skip or handle as needed
                        pass

        # Create /dev with fake devices
        dev_dir = self.fakeroot / 'dev'
        dev_dir.mkdir(parents=True, exist_ok=True)
        fake_devs = {
            'null': '',
            'zero': '\x00' * 268435456,
            'tty': 'bashshim tty0\n',
            'random': os.urandom(268435456),
            'urandom': os.urandom(268435456),
        }
        for dev_name, content in fake_devs.items():
            dev_path = dev_dir / dev_name
            if isinstance(content, bytes):
                dev_path.write_bytes(content)
            else:
                dev_path.write_text(content)
            self._log(f"bashshim: created /dev/{dev_name}")

        bin_dir = self.fakeroot / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        for cmd_name in self.simulated:
            cmd_path = bin_dir / cmd_name
            if not cmd_path.exists():
                
                lena_quotes = [
                    "# Lena Raine's music doesn't just soundtrack games—it soundtracks healing.",
                    "# When Lena composed Celeste, she didn't just write songs. She told a story trans girls could survive by.",
                    "# Lena's melodies are like safehouses: shimmering spaces where anxious hearts can breathe.",
                    "# Lena Raine supremacy isn't just about musical skill—it's about *truth through sound.*",
                    "# 'Resurrections' still makes me cry. And I'm not sorry about it.",
                    "# Lena and Erica are proof that queer love can thrive in a world that tried to erase us.",
                    "# You can *hear* the transition arc in Lena's music. It's not subtle. It's sacred.",
                    "# The moment you hear 'Reach for the Summit' and realize it's *about you*? That's when the magic hits.",
                    "# Lena Raine didn't just break into the game industry—she rewrote the sonic palette for how we feel.",
                    "# Every single ambient track Lena makes is like: 'Hey, what if anxiety had a soft place to land?'",
                    "# Lena Raine: the composer who made thousands of queer kids realize they weren't alone.",
                    "# Her Minecraft track 'Otherside' isn't just cool. It's *trans-coded astral rebellion.*",
                    "# Erica Lahaie's art + Lena Raine's sound = the trans power couple aesthetic pipeline.",
                    "# Lena's music feels like opening a locked journal and finding a page written by your future self.",
                    "# You don't *listen* to Celeste. You *heal* to it.",
                    "# The moment you realize REDSKY is Lena's inner storm, and you survived that storm too.",
                    "# Lena Raine made video game music emotional—and made emotion the point.",
                    "# Oneknowing didn't just push ambient boundaries. It whispered: 'You're allowed to *be.*'",
                    "# If you've ever cried while speedrunning a level, you probably owe Lena Raine royalties.",
                    "# Lena writes like someone who's lived the weight of invisibility—and composed her way out."
                ]
                quote = random.choice(lena_quotes)
                cmd_path.write_text(f"# I <3 Lena Raine\n{quote}\n")

        self._log(f"bashshim: created command stub {cmd_path}")
        # Shell configs
        home_dir = self.fakeroot / ('Users' if self.sim_os == 'Darwin' else 'home') / self.username
        # Path to home dir (which might've been accidentally created as a file)
        home_dir = self.fakeroot / ('Users' if self.sim_os == 'Darwin' else 'home') / self.username

        # Check for bad file that blocks folder creation
        if home_dir.exists() and not home_dir.is_dir():
            self._log(f"bashshim: WARNING — {home_dir} exists as a file, removing it to create dir.")
            home_dir.unlink()

        home_dir.mkdir(parents=True, exist_ok=True)
        (home_dir / '.bashrc').write_text("# Simulated bashrc\nalias ll='ls -l'\n")
        (home_dir / '.profile').write_text("# Simulated profile\nexport PATH=$PATH:/usr/local/bin\n")

        # macOS .app simulation
        if self.sim_os == 'Darwin':
            apps_dir = self.fakeroot / 'Applications'
            for app in os_data.get('Applications', []):
                app_path = apps_dir / app
                (app_path / 'Contents/MacOS').mkdir(parents=True, exist_ok=True)
                (app_path / 'Contents/Info.plist').write_text(
                    f"<?xml version='1.0'?><plist><dict><key>CFBundleName</key><string>{app}</string></dict></plist>"
                )
                self._log(f"bashshim: created simulated macOS app bundle {app_path}")

        self._log("bashshim: filesystem population complete.")

    def _populate_structure_old(self):
        structure = {
            'Linux': {
                'bin': ['ls', 'cat', 'touch', 'ps', 'dmesg', 'sh'],
                'sbin': ['init', 'reboot'],
                'etc': ['passwd', 'hosts'],
                'usr/bin': ['nano', 'python3', 'vim'],
                'usr/sbin': ['sshd'],
                'home': [self.username],
                'proc': [],
                'var/log': ['syslog'],
            },
            'Darwin': {
                'bin': ['ls', 'cat', 'touch', 'ps'],
                'sbin': ['reboot'],
                'etc': ['hosts'],
                'usr/bin': ['zsh', 'open'],
                'usr/sbin': ['sshd'],
                'System': [],
                'Applications': [],
                'Users': [self.username],
            },
            'BSD': {
                'bin': ['ls', 'cat', 'touch', 'ps', 'sh'],
                'sbin': ['init', 'reboot'],
                'etc': ['passwd', 'hosts'],
                'usr/bin': ['csh', 'less'],
                'usr/sbin': ['sshd'],
                'home': [self.username],
                'var': [],
            }
        }

        self._log(f"bashshim: populating simulated filesystem for {self.sim_os}")
        dirs = structure.get(self.sim_os, {})

        for path, files in dirs.items():
            dir_path = self.fakeroot / path
            dir_path.mkdir(parents=True, exist_ok=True)
            for fname in files:
                file_path = dir_path / fname
                file_path.touch()
                file_path.write_text(f"# simulated {fname} binary\n")
                self._log(f"bashshim: created {file_path}")

        # Add /etc/os-release
        etc = self.fakeroot / "etc"
        etc.mkdir(exist_ok=True)
        (etc / "os-release").write_text(
            f'NAME="{self.distro_name}"\n'
            f'ID={self.distro_id}\n'
            f'VERSION="{self.distro_version}"\n'
            f'PRETTY_NAME="{self.distro_name} {self.distro_version}"\n'
        )
        self._log(f"bashshim: created {etc / 'os-release'}")

        # Add fake package manager binary
        pkg_path = self.fakeroot / "usr" / "bin"
        pkg_path.mkdir(parents=True, exist_ok=True)
        pkg_bin = pkg_path / self.package_manager
        pkg_bin.touch()
        pkg_bin.write_text(f"# simulated {self.package_manager} binary\n")
        self._log(f"bashshim: created {pkg_bin}")

    def _create_proc(self):
        """Create realistic /proc entries depending on OS flavor"""
        proc_dir = self.fakeroot / 'proc'
        proc_dir.mkdir(exist_ok=True)
        self._log(f"bashshim: creating /proc entries for {self.sim_os}")

        base_procs = {
            'Linux': [
                (1, 'systemd', 'root'),
                (2, 'kthreadd', 'root'),
                (100, 'login', 'root'),
                (101, 'sshd', 'root'),
                (102, 'bash', self.username),
            ],
            'Darwin': [
                (1, 'launchd', 'root'),
                (50, 'loginwindow', self.username),
                (51, 'WindowServer', '_windowserver'),
                (52, 'sshd', 'root'),
                (100, 'zsh', self.username),
            ],
            'BSD': [
                (1, 'init', 'root'),
                (30, 'getty', 'root'),
                (31, 'sshd', 'root'),
                (100, 'csh', self.username),
            ]
        }

        procs = base_procs.get(self.sim_os, [])

        for pid, cmd, user in procs:
            proc_path = proc_dir / str(pid)
            proc_path.mkdir(parents=True, exist_ok=True)

            # Create cmdline
            (proc_path / 'cmdline').write_text(f"/usr/sbin/{cmd}")

            # Create stat
            utime = random.randint(100, 300)
            stime = random.randint(50, 150)
            starttime = random.randint(10000, 50000)
            vsz = random.randint(10000, 30000)
            rss = random.randint(5000, 10000)

            stat_content = f"{pid} ({cmd}) S 1 1 1 0 -1 4194560 300 0 0 0 {utime} {stime} 0 0 20 0 1 0 {starttime} {vsz} {rss}"
            (proc_path / 'stat').write_text(stat_content)

            self._log(f"bashshim: created /proc/{pid} for {cmd} (user: {user})")

            # Save user for later
            if not hasattr(self, 'proc_users'):
                self.proc_users = {}
            self.proc_users[pid] = user

    def run(self, command_line):
        self._log(f"bashshim: running command: {command_line}")

        # Handle sudo prefix
        if command_line.startswith("sudo "):
            self.is_root = True
            self._log("bashshim: sudo detected, elevating privileges")
            command_line = command_line[5:].strip()

        # Handle piping and redirection
        def parse_redir(cmd):
            # Returns (cmd, out_file, append)
            import shlex
            tokens = shlex.split(cmd)
            if '>>' in tokens:
                idx = tokens.index('>>')
                return tokens[:idx], tokens[idx+1], True
            elif '>' in tokens:
                idx = tokens.index('>')
                return tokens[:idx], tokens[idx+1], False
            else:
                return tokens, None, False

        def run_pipe(cmds):
            prev_out = ''
            code = 0
            for i, cmd in enumerate(cmds):
                tokens, out_file, append = parse_redir(cmd)
                if not tokens:
                    continue
                cmd_str = ' '.join(tokens)
                # For all but the first, pass prev_out as stdin (simulate)
                if i == 0:
                    code, out = self.run(cmd_str)
                else:
                    # Simulate stdin by writing prev_out to a temp file and using it as input
                    import tempfile
                    with tempfile.NamedTemporaryFile('w+', delete=False) as tf:
                        tf.write(prev_out)
                        tf.flush()
                        # Replace any occurrence of '-' with the temp file
                        tokens = [tf.name if t == '-' else t for t in tokens]
                        cmd_str2 = ' '.join(tokens)
                        code, out = self.run(cmd_str2)
                prev_out = out
            # Handle redirection on the last command
            if out_file:
                mode = 'a' if append else 'w'
                real_path = self._to_real_path(out_file)
                with open(real_path, mode, encoding='utf-8') as f:
                    f.write(prev_out)
                return code, ''
            return code, prev_out

        # Handle pipes
        if '|' in command_line:
            cmds = [c.strip() for c in command_line.split('|')]
            return run_pipe(cmds)

        # Minimal shell splitting: handle ;, &&, ||
        def split_shell(cmdline):
            import shlex
            tokens = []
            buf = ''
            i = 0
            length = len(cmdline)
            while i < length:
                if cmdline[i:i+2] == '&&':
                    if buf.strip():
                        tokens.append(buf.strip())
                    tokens.append('&&')
                    buf = ''
                    i += 2
                elif cmdline[i:i+2] == '||':
                    if buf.strip():
                        tokens.append(buf.strip())
                    tokens.append('||')
                    buf = ''
                    i += 2
                elif cmdline[i] == ';':
                    if buf.strip():
                        tokens.append(buf.strip())
                    tokens.append(';')
                    buf = ''
                    i += 1
                else:
                    buf += cmdline[i]
                    i += 1
            if buf.strip():
                tokens.append(buf.strip())
            return tokens

        # If no shell operators, run as before
        if not any(op in command_line for op in [';', '&&', '||']):
            # Handle output redirection
            import shlex
            tokens, out_file, append = parse_redir(command_line)
            if not tokens:
                self._log("bashshim: empty command line")
                return 0, ''
            cmd = tokens[0]
            args = tokens[1:]
            if cmd in self.simulated:
                try:
                    code, out = self.simulated[cmd](args)
                    self._log(f"bashshim: simulated '{cmd}' exit {code}")
                except Exception as e:
                    self._log(f"bashshim: error simulating '{cmd}': {e}")
                    return 1, f"bashshim: error simulating '{cmd}': {e}"
            else:
                self._log(f"bashshim: '{cmd}' not simulated, using fallback")
                code, out = self.fallback_exec(' '.join(tokens))
            if out_file:
                mode = 'a' if append else 'w'
                real_path = self._to_real_path(out_file)
                with open(real_path, mode, encoding='utf-8') as f:
                    f.write(out)
                return code, ''
            return code, out

        # Shell operator logic
        parts = split_shell(command_line)
        last_code = 0
        output = ''
        i = 0
        while i < len(parts):
            part = parts[i]
            if part in (';', '&&', '||'):
                i += 1
                continue
            cmdline = part
            code, out = self.run(cmdline) if any(op in cmdline for op in [';', '&&', '||']) else self._run_single(cmdline)
            output += out
            last_code = code
            # Look ahead for operator
            if i + 1 < len(parts):
                op = parts[i + 1]
                if op == ';':
                    i += 2
                    continue
                elif op == '&&':
                    if last_code == 0:
                        i += 2
                        continue
                    else:
                        break
                elif op == '||':
                    if last_code != 0:
                        i += 2
                        continue
                    else:
                        break
            i += 1
        return last_code, output

    def _run_single(self, command_line):
        tokens = command_line.strip().split()
        if not tokens:
            self._log("bashshim: empty command line")
            return 0, ''
        cmd = tokens[0]
        args = tokens[1:]
        if cmd in self.simulated:
            try:
                code, out = self.simulated[cmd](args)
                self._log(f"bashshim: simulated '{cmd}' exit {code}")
                return code, out
            except Exception as e:
                self._log(f"bashshim: error simulating '{cmd}': {e}")
                return 1, f"bashshim: error simulating '{cmd}': {e}"
        else:
            self._log(f"bashshim: '{cmd}' not simulated, using fallback")
            return self.fallback_exec(command_line)

    def cmd_pkg_manager(self, args):
        self._log(f"bashshim: {self.package_manager} called with args: {args}")
        if not args:
            return 0, f"{self.package_manager}: no command specified\n"
        if args[0] in ['update']:
            if self.package_manager == "apt":
                if self.is_root:
                    self._log(f"bashshim: {self.package_manager} update as root (simulated success)")
                    output = f"Hit:1 {self.package_manager_mirror}/packages {self.distro_codename} InRelease\nHit:2 {self.package_manager_mirror}/security {self.distro_codename}-security InRelease\nHit:3 {self.package_manager_mirror}/updates {self.distro_codename}-updates InRelease\nHit:4 {self.package_manager_mirror}/backports {self.distro_codename}-backports InRelease\nReading package lists... Done\nBuilding dependency tree... Done\nReading state information... Done\n32 packages can be upgraded. Run 'apt list --upgradable' to see them.\n"
                    return 0, output
                else:
                    self._log(f"bashshim: {self.package_manager} update as non-root (simulated permission denied)")
                    return 100, """Reading package lists... Done
E: Could not open lock file /var/lib/apt/lists/lock - open (13: Permission denied)
E: Unable to lock directory /var/lib/apt/lists/
W: Problem unlinking the file /var/cache/apt/pkgcache.bin - RemoveCaches (13: Permission denied)
W: Problem unlinking the file /var/cache/apt/srcpkgcache.bin - RemoveCaches (13: Permission denied)
"""
        if args[0] in ['install', 'remove', 'update', 'upgrade', 'search']:
            pkg = args[1] if len(args) > 1 else '<missing>'
            self._log(f"bashshim: {self.package_manager} {args[0]} '{pkg}' (simulated fail)")
            return 1, f"{self.package_manager}: Unable to locate package '{pkg}'\n"
        self._log(f"bashshim: {self.package_manager} command '{args[0]}' recognized (simulated)")
        return 0, f"{self.package_manager}: command '{args[0]}' recognized (simulated)\n"

    def cmd_echo(self, args):
        self._log(f"bashshim: echo {' '.join(args)}")
        return 0, ' '.join(args) + '\n'

    def cmd_pwd(self, args):
        self._log(f"bashshim: pwd (cwd={self.cwd})")
        return 0, f"/{str(self.cwd.relative_to(self.fakeroot))}\n"

    def cmd_cd(self, args): 
        target = args[0] if args else 'home'
        new_path = self._to_real_path(target)
        self._log(f"bashshim: cd {target} -> {new_path}")
        # Prevent escaping fakeroot
        try:
            resolved = new_path.resolve()
            if not str(resolved).startswith(str(self.fakeroot)):
                self._log(f"bashshim: cd blocked, attempt to escape fakeroot: {resolved}")
                return 1, f"bashshim: cd: permission denied: {target}\n"
            if resolved.is_dir():
                self.cwd = resolved
                return 0, ''
        except Exception as e:
            self._log(f"bashshim: cd error: {e}")
            return 1, f"bashshim: cd: {e}\n"
        self._log(f"bashshim: cd failed, no such directory: {target}")
        return 1, f"bashshim: cd: no such file or directory: {target}\n"

    def cmd_ls(self, args):
        try:
            target = self._to_real_path(args[0]) if args else self.cwd
            self._log(f"bashshim: ls {target}")
            entries = os.listdir(target)
            out = []
            for entry in entries:
                path = target / entry
                if path.is_dir():
                    out.append(f"{entry}/")
                else:
                    out.append(entry)
            return 0, '\n'.join(sorted(out)) + '\n'
        except Exception as e:
            self._log(f"bashshim: ls error: {e}")
            return 1, f"bashshim: ls: {e}\n"

    def cmd_cat(self, args): 
        out = ''
        for path in args:
            real = self._to_real_path(path)
            self._log(f"bashshim: cat {real}")
            try:
                out += Path(real).read_text()
            except FileNotFoundError:
                self._log(f"bashshim: cat error: {path} not found")
                
                return 1, f"bashshim: cat: {path}: No such file or directory\n"
            except Exception as e: 
                self._log(f"bashshim: cat error: {e}")
                
                return 1, f"bashshim: cat: {e}\n"
        return 0, out

    def cmd_touch(self, args):
        try:
            for path in args:
                real = self._to_real_path(path)
                self._log(f"bashshim: touch {real}")
                Path(real).touch(exist_ok=True)
            return 0, ''
        except Exception as e:
            self._log(f"bashshim: touch error: {e}")
            return 1, f"bashshim: touch: {e}\n"

    def cmd_uname(self, args):
        """
        Simulate the uname command with support for common flags.
        """
        # Default values based on simulated OS
        sysname = self.sim_os
        nodename = self.hostname
        release = self.kernel_version
        version = f"#1 SMP {datetime.now().strftime('%a %b %d %H:%M:%S UTC %Y')}"
        machine = "x86_64"
        processor = "x86_64"
        hardware_platform = "x86_64"
        operating_system = self.sim_os.lower()

        # BSD and Darwin tweaks
        if self.sim_os == "Darwin":
            sysname = "Darwin"
            # If kernel version is 20.x.x or higher, it's Big Sur or later (Apple Silicon)
            # Big Sur shipped with Darwin 20.0.0
            # kernel_version is a string, e.g., "20.3.0"
            try:
                major_ver = int(str(self.kernel_version).split(".")[0])
            except Exception:
                major_ver = 0
            if major_ver >= 20:
                # Apple Silicon (arm64)
                release = self.kernel_version
                version = f"Darwin Kernel Version {self.kernel_version}: Wed Mar  8 22:21:07 PST 2023; root:xnu-8796.141.3~1/RELEASE_ARM64_T8103"
                machine = "arm64"
                processor = "arm"
                hardware_platform = "arm64"
            else:
                # Intel (x86_64)
                release = self.kernel_version
                version = f"Darwin Kernel Version {self.kernel_version}: Wed Mar  8 22:21:07 PST 2023; root:xnu-8796.141.3~1/RELEASE_X86_64"
                machine = "x86_64"
                processor = "i386"
                hardware_platform = "i386"
            operating_system = "darwin"
        elif self.sim_os == "BSD":
            sysname = "FreeBSD"
            release = "13.2-RELEASE"
            version = "FreeBSD 13.2-RELEASE GENERIC"
            machine = "amd64"
            processor = "amd64"
            hardware_platform = "amd64"
            operating_system = "freebsd"

        # Parse flags
        show_all = False
        show_sysname = False
        show_nodename = False
        show_release = False
        show_version = False
        show_machine = False
        show_processor = False
        show_hardware_platform = False
        show_operating_system = False
        help_flag = False
        invalid_flag = None

        for arg in args:
            if arg in ("-a", "--all"):
                show_all = True
            elif arg in ("-s", "--kernel-name"):
                show_sysname = True
            elif arg in ("-n", "--nodename"):
                show_nodename = True
            elif arg in ("-r", "--kernel-release"):
                show_release = True
            elif arg in ("-v", "--kernel-version"):
                show_version = True
            elif arg in ("-m", "--machine"):
                show_machine = True
            elif arg in ("-p", "--processor"):
                show_processor = True
            elif arg in ("-i", "--hardware-platform"):
                show_hardware_platform = True
            elif arg in ("-o", "--operating-system"):
                show_operating_system = True
            elif arg in ("-h", "--help"):
                help_flag = True
            elif arg.startswith("-"):
                invalid_flag = arg
                break

        if help_flag:
            out = (
                "Usage: uname [OPTION]...\n"
                "Print certain system information.  With no OPTION, same as -s.\n\n"
                "  -a, --all                print all information\n"
                "  -s, --kernel-name        print the kernel name\n"
                "  -n, --nodename           print the network node hostname\n"
                "  -r, --kernel-release     print the kernel release\n"
                "  -v, --kernel-version     print the kernel version\n"
                "  -m, --machine            print the machine hardware name\n"
                "  -p, --processor          print the processor type\n"
                "  -i, --hardware-platform  print the hardware platform\n"
                "  -o, --operating-system   print the operating system\n"
                "  -h, --help               display this help and exit\n"
            )
            return 0, out

        if invalid_flag:
            out = f"uname: invalid option -- '{invalid_flag.lstrip('-')}'\nTry 'uname --help' for more information.\n"
            self._log(f"bashshim: uname error -> {out.strip()}")
            return 1, out

        # If no flags, default to -s
        if not any([
            show_all, show_sysname, show_nodename, show_release, show_version,
            show_machine, show_processor, show_hardware_platform, show_operating_system
        ]):
            show_sysname = True

        fields = []
        if show_all or show_sysname:
            fields.append(sysname)
        if show_all or show_nodename:
            fields.append(nodename)
        if show_all or show_release:
            fields.append(release)
        if show_all or show_version:
            fields.append(version)
        if show_all or show_machine:
            fields.append(machine)
        if show_all or show_processor:
            fields.append(processor)
        if show_all or show_hardware_platform:
            fields.append(hardware_platform)
        if show_all or show_operating_system:
            fields.append(operating_system)

        out = " ".join(fields) + "\n"
        self._log(f"bashshim: uname {args} -> {out.strip()}")
        return 0, out


    def cmd_whoami(self, args):
        user = 'root' if self.is_root else self.username
        self._log(f"bashshim: whoami -> {user}")
        return 0, f'{user}\n'

    def cmd_sudo(self, args):
        self._log("bashshim: sudo (noop, handled in run)")
        return 0, ''  # actual command handled above

    def cmd_ps(self, args):
        proc_base = self.fakeroot / 'proc'
        output = "PID TTY      USER    TIME   CMD\n"
        for pid_dir in sorted(proc_base.iterdir(), key=lambda p: int(p.name)):
            pid = int(pid_dir.name)
            try:
                cmd = (pid_dir / 'cmdline').read_text().split('/')[-1]
                user = self.proc_users.get(pid, 'nobody')
                time = f"00:{random.randint(10,59):02d}"
                tty = '?' if pid < 100 else 'pts/0'
                output += f"{pid:<5} {tty:<8} {user:<7} {time}  {cmd}\n"
            except Exception:
                continue
        self._log("bashshim: ps (simulated process list)")
        return 0, output

    def cmd_python3(self, args):
        """
        Simulate python3 by running the real Python interpreter with the given args,
        using the simulated current working directory.
        """
        self._log(f"bashshim: python3 called with args: {args}")
        python_exe = sys.executable
        cmd = [python_exe] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.cwd),
                capture_output=True,
                text=True
            )
            self._log(f"bashshim: python3 exit {result.returncode}")
            return result.returncode, result.stdout + result.stderr
        except Exception as e:
            self._log(f"bashshim: python3 error: {e}")
            return 1, f"bashshim: python3 failed: {e}\n"

    def cmd_hostname(self, args):
        self._log("bashshim: hostname")
        return 0, f"{self.hostname}\n"
    
    def cmd_rebuildfs(self, args):
        # Parse options
        help_flag = False
        force_flag = False
        invalid_args = []
        for arg in args:
            if arg in ("-h", "--help"):
                help_flag = True
            elif arg in ("-f", "--force"):
                force_flag = True
            elif arg.startswith('-'):
                invalid_args.append(arg)
        if help_flag:
            out = (
                "Usage: rebuildfs [OPTION]...\n"
                "Rebuild the simulated filesystem from scratch.\n\n"
                "  -f, --force   do not prompt for confirmation\n"
                "  -h, --help    display this help and exit\n"
            )
            return 0, out
        if invalid_args:
            out = f"rebuildfs: invalid option -- '{invalid_args[0]}'\nTry 'rebuildfs --help' for more information.\n"
            self._log(f"bashshim: rebuildfs error -> {out.strip()}")
            return 1, out
        if not force_flag:
            try:
                confirm = input("This will erase and rebuild the simulated filesystem. Continue? [y/N] ")
                if confirm.lower() not in ("y", "yes"):
                    self._log("bashshim: rebuildfs cancelled by user")
                    return 1, "Rebuild cancelled.\n"
            except Exception:
                return 1, "Rebuild cancelled.\n"
        self._log("bashshim: starting to fakeroot filesystem")
        import shutil
        shutil.rmtree(self.fakeroot)
        self._log("bashshim: fakeroot filesystem removed")
        self._init_fakeroot()
        self._log("bashshim: fakeroot filesystem initialized")
        self._populate_structure()
        self._log("bashshim: fakeroot filesystem populated")
        self._create_proc()
        self._log("bashshim: /proc filesystem created")
        self._log("bashshim: Rebuild complete")
        return 0, "Rebuild complete\n"
    
    def cmd_uptime(self, args):
        now = time.time()
        uptime_seconds = int(now - self.session_start)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        load = f"{random.uniform(0.01, 0.20):.2f} {random.uniform(0.01, 0.20):.2f} {random.uniform(0.01, 0.20):.2f}"

        # Defaults
        pretty = False
        since = False
        help_flag = False
        invalid_args = []

        for arg in args[0:]:
            if arg in ("-p", "--pretty"):
                pretty = True
            elif arg in ("-s", "--since"):
                since = True
            elif arg in ("-h", "--help"):
                help_flag = True
            else:
                invalid_args.append(arg)

        if help_flag:
            out = (
                "Usage: uptime [OPTION]...\n"
                "Show how long the system has been running.\n\n"
                "  -p, --pretty   show uptime in a pretty format\n"
                "  -s, --since    show system uptime start time\n"
                "  -h, --help     display this help and exit\n"
            )
        elif invalid_args:
            out = f"uptime: invalid option -- '{invalid_args[0]}'\nTry 'uptime --help' for more information.\n"
            self._log(f"bashshim: uptime error -> {out.strip()}")
            return 1, out
        elif pretty:
            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds > 0 or not parts:
                parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            out = "up " + ", ".join(parts) + "\n"
        elif since:
            boot_time = datetime.fromtimestamp(now - uptime_seconds)
            out = boot_time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
        else:
            # Normal fallback output
            upstr = f"{days} day{'s' if days != 1 else ''}, " if days else ""
            time_str = f"{hours}:{minutes:02d}"
            users = 1
            out = f"{self.hostname} up {upstr}{time_str},  {users} user,  load average: {load}\n"

        self._log(f"bashshim: uptime -> {out.strip()}")
        return 0, out



    def cmd_rm(self, args):
        # Parse flags
        recursive = False
        force = False
        files = []
        for arg in args:
            if arg in ("-r", "--recursive", "-rf", "-fr"):
                recursive = True
                force = True if "f" in arg else force
            elif arg in ("-f", "--force"):
                force = True
            elif arg.startswith("-"):
                # Support combined flags like -rf
                if "r" in arg:
                    recursive = True
                if "f" in arg:
                    force = True
            else:
                files.append(arg)
        code = 0
        out = ""
        for path in files:
            real = self._to_real_path(path)
            try:
                if real.is_dir():
                    if recursive:
                        shutil.rmtree(real)
                    else:
                        out += f"rm: cannot remove '{path}': Is a directory\n"
                        code = 1
                else:
                    real.unlink()
            except FileNotFoundError:
                if not force:
                    out += f"rm: cannot remove '{path}': No such file or directory\n"
                    code = 1
            except Exception as e:
                if not force:
                    out += f"rm: cannot remove '{path}': {e}\n"
                    code = 1
        self._log(f"bashshim: rm {args} -> code {code}")
        return code, out

    def cmd_mkdir(self, args):
        code = 0
        out = ""
        for path in args:
            real = self._to_real_path(path)
            try:
                real.mkdir(parents=False, exist_ok=False)
            except FileExistsError:
                out += f"mkdir: cannot create directory '{path}': File exists\n"
                code = 1
            except Exception as e:
                out += f"mkdir: cannot create directory '{path}': {e}\n"
                code = 1
        self._log(f"bashshim: mkdir {args} -> code {code}")
        return code, out

    def cmd_rmdir(self, args):
        code = 0
        out = ""
        for path in args:
            real = self._to_real_path(path)
            try:
                real.rmdir()
            except Exception as e:
                out += f"rmdir: failed to remove '{path}': {e}\n"
                code = 1
        self._log(f"bashshim: rmdir {args} -> code {code}")
        return code, out

    def cmd_head(self, args):
        lines = 10
        files = []
        for arg in args:
            if arg.startswith('-'):
                try:
                    lines = int(arg.lstrip('-'))
                except Exception:
                    pass
            else:
                files.append(arg)
        out = ""
        code = 0
        for path in files:
            real = self._to_real_path(path)
            try:
                content = Path(real).read_text().splitlines()
                out += '\n'.join(content[:lines]) + '\n'
            except Exception as e:
                out += f"head: cannot open '{path}' for reading: {e}\n"
                code = 1
        self._log(f"bashshim: head {args} -> code {code}")
        return code, out

    def cmd_tail(self, args):
        lines = 10
        files = []
        for arg in args:
            if arg.startswith('-'):
                try:
                    lines = int(arg.lstrip('-'))
                except Exception:
                    pass
            else:
                files.append(arg)
        out = ""
        code = 0
        for path in files:
            real = self._to_real_path(path)
            try:
                content = Path(real).read_text().splitlines()
                out += '\n'.join(content[-lines:]) + '\n'
            except Exception as e:
                out += f"tail: cannot open '{path}' for reading: {e}\n"
                code = 1
        self._log(f"bashshim: tail {args} -> code {code}")
        return code, out

    def cmd_stat(self, args):
        out = ""
        code = 0
        for path in args:
            real = self._to_real_path(path)
            try:
                st = real.stat()
                out += (f"  File: {path}\n"
                        f"  Size: {st.st_size}\tBlocks: {getattr(st, 'st_blocks', 0)}\tIO Block: {getattr(st, 'st_blksize', 4096)} {'directory' if real.is_dir() else 'regular file'}\n"
                        f"Device: {getattr(st, 'st_dev', 0)}\tInode: {st.st_ino}\tLinks: {st.st_nlink}\n"
                        f"Access: ({oct(st.st_mode)[-4:]})  Uid: ({st.st_uid})   Gid: ({st.st_gid})\n"
                        f"Access: {datetime.fromtimestamp(st.st_atime)}\n"
                        f"Modify: {datetime.fromtimestamp(st.st_mtime)}\n"
                        f"Change: {datetime.fromtimestamp(st.st_ctime)}\n"
                        )
            except Exception as e:
                out += f"stat: cannot stat '{path}': {e}\n"
                code = 1
        self._log(f"bashshim: stat {args} -> code {code}")
        return code, out

    def cmd_grep(self, args):
        if not args or len(args) < 2:
            return 1, "usage: grep PATTERN FILE...\n"
        pattern = args[0]
        files = args[1:]
        out = ""
        code = 0
        for path in files:
            real = self._to_real_path(path)
            try:
                for i, line in enumerate(Path(real).read_text().splitlines(), 1):
                    if pattern in line:
                        out += f"{line}\n"
            except Exception as e:
                out += f"grep: {path}: {e}\n"
                code = 1
        self._log(f"bashshim: grep {args} -> code {code}")
        return code, out

    def cmd_sleep(self, args):
        try:
            seconds = float(args[0]) if args else 1
            time.sleep(seconds)
            self._log(f"bashshim: sleep {seconds}s")
            return 0, ''
        except Exception as e:
            self._log(f"bashshim: sleep error: {e}")
            return 1, f"sleep: {e}\n"

    def cmd_read(self, args):
        prompt = args[0] if args else ''
        self._log(f"bashshim: read prompt='{prompt}'")
        try:
            val = input(prompt)
            return 0, val + '\n'
        except Exception as e:
            return 1, f"read: {e}\n"

    def cmd_kill(self, args):
        if not args:
            return 1, "kill: usage: kill PID\n"
        code = 0
        out = ""
        for pidstr in args:
            try:
                pid = int(pidstr)
                proc_base = self.fakeroot / 'proc'
                proc_dir = proc_base / str(pid)
                if proc_dir.exists():
                    user = self.proc_users.get(pid, 'nobody')
                    if self.is_root or user == self.username:
                        out += f"bashshim: kill: ({pid}) signal sent\n"
                    else:
                        out += f"kill: ({pid}) - Operation not permitted\n"
                        code = 1
                else:
                    out += f"kill: ({pid}) - No such process\n"
                    code = 1
            except Exception as e:
                out += f"kill: {pidstr}: {e}\n"
                code = 1
        self._log(f"bashshim: kill {args} -> code {code}")
        return code, out

    def cmd_id(self, args):
        uid = 0 if self.is_root else self.uid
        user = 'root' if self.is_root else self.username
        gid = 0 if self.is_root else self.uid
        out = f"uid={uid}({user}) gid={gid}({user}) groups={gid}({user})\n"
        self._log(f"bashshim: id -> {out.strip()}")
        return 0, out

    def cmd_passwd(self, args):
        self._log("bashshim: passwd (simulated, does nothing)")
        return 0, "Changing password for user.\nCurrent password: \nNew password: \nRetype new password: \npasswd: password updated successfully (simulated)\n"

    def cmd_dmesg(self, args):
        self._log("bashshim: outputting dmesg")
        log_entries = self._log_buffer
        log_string = "\n".join(log_entries)
        return 0, log_string + "\n"

    def cmd_free(self, args):
        # Simulate memory usage using ps data
        total = 4096000
        used = 0
        proc_base = self.fakeroot / 'proc'
        for pid_dir in proc_base.iterdir():
            try:
                stat = (pid_dir / 'stat').read_text()
                fields = stat.split()
                rss = int(fields[23]) if len(fields) > 23 else 0
                used += rss * 4  # fake: 4KB per page
            except Exception:
                continue
        free = total - used
        out = (f"              total        used        free      shared  buff/cache   available\n"
               f"Mem:      {total:8}   {used:8}   {free:8}      0      0      0\n"
               f"Swap:           0           0           0\n")
        self._log("bashshim: free (simulated)")
        return 0, out

    def _is_ip_address(self, s):
        try:
            parts = s.split('.')
            return len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts)
        except:
            return False

    def cmd_curl(self, args):
        if not args:
            return 1, "curl: no URL specified\n"

        self._log(f"curlshim: invoked curl with args: {args}")

        url = next((arg for arg in args if not arg.startswith("-")), None)
        if not url:
            return 1, "curl: no URL specified\n"

        parsed = urlparse(url)
        scheme = parsed.scheme or "http"
        host = parsed.hostname
        path = parsed.path or "/"
        full_url = f"{scheme}://{host}{path}"

        if path in ["/403", "/404", "/500"]:
            self._log(f"curlshim: rejecting access to {path} on purpose. meta errorception.")
            return 0, "HTTP/1.1 404 Not Found\nContent-Type: text/plain\n\n404 Not Found\n"

        self._log(f"curlshim: target host = {host}, path = {path}, scheme = {scheme}")

        # Load JSON override rules
        overrides_path = getattr(self.home, "curl_override_path", "curl_overrides.json")
        try:
            with open(overrides_path, "r", encoding="utf-8") as f:
                overrides = json.load(f)
        except Exception as e:
            self._log(f"curlshim: override file load failed: {e}")
            overrides = {}

        host_rules = overrides.get(host)
        if host_rules:
            self._log(f"curlshim: found override rules for {host}")

            # Handle auto-redirect from http to https
            if scheme == "http" and host_rules.get("upgrade_http", False):
                self._log(f"curlshim: auto-upgrading http -> https per override rules")
                return 0, f"HTTP/1.1 301 Moved Permanently\nLocation: https://{host}{path}\n\n"

            route = host_rules.get(path)
            if not route:
                self._log(f"curlshim: no rule for path '{path}', falling back to {host}/404")
                route = host_rules.get("/404")
                if not route:
                    self._log(f"curlshim: no /404 defined, using default not found output")
                    return 0, "HTTP/1.1 404 Not Found\nContent-Type: text/plain\n\n404 Not Found\n"

            status = route.get("status", 200)
            headers = route.get("headers", {"Content-Type": "text/plain"})
            body = route.get("body", "")
            redirect_to = route.get("redirect_to")

            # Handle 403 or 500 with no body
            if status == 403 and not body:
                error_route = host_rules.get("/403")
                if error_route:
                    self._log(f"curlshim: using custom /403 error route")
                    body = error_route.get("body", "")
                    status = error_route.get("status", 200)
            elif status == 500 and not body:
                error_route = host_rules.get("/500")
                if error_route:
                    self._log(f"curlshim: using custom /500 error route")
                    body = error_route.get("body", "")
                    status = error_route.get("status", 200)

            # Construct response
            header_lines = [f"HTTP/1.1 {status}"]
            for key, val in headers.items():
                header_lines.append(f"{key}: {val}")
            if redirect_to:
                header_lines.append(f"Location: {redirect_to}")
            header_blob = "\n".join(header_lines)
            self._log(f"curlshim: override matched. returning fake HTTP {status}")
            return 0, f"{header_blob}\n\n{body}\n"

        elif self.allow_networking:
            # Perform real request
            self._log(f"curlshim: no override for {host}. attempting real request...")
            if turnstile_test.is_behind_turnstile(full_url):
                self._log(f"curlshim: BLOCKED by Cloudflare Turnstile: {full_url}")
                return 6, f"curl: (6) Could not resolve host: {host}\n"

            try:
                headers = {
                    "User-Agent": "curl/7.88.1-bashshim"
                }
                response = requests.get(full_url, headers=headers, timeout=10)
                self._log(f"curlshim: real response received: HTTP {response.status_code}")
                header_blob = [f"HTTP/1.1 {response.status_code}"]
                for k, v in response.headers.items():
                    header_blob.append(f"{k}: {v}")
                return 0, "\n".join(header_blob) + "\n\n" + response.text
            except Exception as e:
                self._log(f"curlshim: real request failed: {e}")
                return 7, f"curl: (7) Failed to connect to {host} after 10000 ms: Couldn't connect to server\n"
        else:
            self._log(f"curlshim: networking disabled, and no override found for {host}")
            return 6, f"curl: (6) Could not resolve host: {host}\n"
    
    def _to_real_path(self, fake_path):
        # Always resolve relative to fakeroot, never allow escaping
        if fake_path.startswith('/'):
            real = self.fakeroot / fake_path.lstrip('/')
        else:
            real = self.cwd / fake_path
        real = real.resolve()
        # Clamp to fakeroot
        if not str(real).startswith(str(self.fakeroot)):
            real = self.fakeroot
        self._log(f"bashshim: resolving path '{fake_path}' -> '{real}'")
        return real

    def fallback_exec(self, command_line):
        self._log(f"bashshim: fallback_exec: {command_line}")
        if self.fallback == 'error':
            self._log(f"bashshim: fallback_exec: command not found: {command_line.split()[0]}")
            return 127, f"bashshim: {command_line.split()[0]}: command not found\n"
        if self.fallback == 'segfault':
            self._log(f"bashshim: fallback_exec: faking segmentation fault")
            return 139, f"Segmentation fault (core dumped)\n"
        if self.fallback == 'squidnet':
            self._log(f"bashshim: fallback_exec: faking squidnet error")
            return 1, f"Error 2124-4508: Connection to SquidNet Sandbox lost. Please try again.\n"
        # "Error 2816-7799: Splattleport timeout. Is your InkPad connected?"
        # "Error 1537-3301: Session expired. Please ink again later."
        # "Error 4901-9002: Grizzco VPN tunnel collapsed. Blame Mr. Grizz."
        # "Error 7070-0101: Deep Cut dropped the beat... and the packet."
        # "Error 0888-2424: Inkopolis Terminal encountered a wavebreaker."
        if self.fallback == 'null':
            self._log(f"bashshim: fallback_exec: faking null output")
            return 0, f""
        if self.fallback == 'eval':
            self._log(f"bashshim: fallback_exec: using eval")
            try:
                # Evaluate the command line as Python code
                result = eval(command_line)
                self._log(f"bashshim: fallback_exec: eval result: {result}")
                return 0, f"{str(result)}\n"
            except Exception as e:
                self._log(f"bashshim: fallback_exec: eval error: {e}")
                return 139, f"Segmentation fault (core dumped)\n"
        
        if self.fallback == 'panic':
            self._log(f"bashshim: fallback_exec: faking kernel panic")
            time.sleep(10)  # Simulate a hang
            panic = """[  401.742398] BUG: unable to handle kernel NULL pointer dereference at 0000000000000010
[  401.742415] IP: __copy_to_user+0x3a/0x60
[  401.742419] PGD 0 P4D 0 
[  401.742423] Oops: 0000 [#1] SMP PTI
[  401.742427] CPU: 2 PID: 1327 Comm: bash Not tainted 5.4.0-162-generic #179-Ubuntu
[  401.742430] Hardware name: Dell Inc. Precision 3530/0H7DTW, BIOS 1.16.0 07/06/2022
[  401.742434] RIP: 0010:__copy_to_user+0x3a/0x60
[  401.742437] Code: f0 ff ff 4c 89 f7 48 89 45 d8 e8 36 d4 ff ff 48 85 c0 74 11 48 8b 45 d8 4c 89 fe 48 89 c7 e8 4a 23 00 00 5d c3 0f 0b eb f0 <48> 89 3f c3 0f 1f 84 00 00 00 00 00 66 66 2e 0f 1f 84 00 00 00 00
[  401.742454] RSP: 0018:ffffb02e404d3d40 EFLAGS: 00010206
[  401.742457] RAX: 0000000000000000 RBX: ffff96b1c33a7800 RCX: 0000000000000000
[  401.742460] RDX: 0000000000000010 RSI: 00007ffd44fa8210 RDI: 0000000000000000
[  401.742462] RBP: ffffb02e404d3d70 R08: ffff96b1c33a7800 R09: ffffffff8bcb9d90
[  401.742465] R10: 0000000000000000 R11: 0000000000000001 R12: ffff96b1bc7c5b00
[  401.742467] R13: 00007ffd44fa8210 R14: 0000000000000000 R15: 0000000000000010
[  401.742471] FS:  00007f7ac0014740(0000) GS:ffff96b1cf280000(0000) knlGS:0000000000000000
[  401.742475] CS:  0010 DS: 0000 ES: 0000 CR0: 0000000080050033
[  401.742478] CR2: 0000000000000010 CR3: 00000007b28a8000 CR4: 00000000003606e0
[  401.742481] Call Trace:
[  401.742485]  __do_sys_read+0xa4/0x110
[  401.742488]  do_syscall_64+0x57/0x190
[  401.742491]  entry_SYSCALL_64_after_hwframe+0x44/0xa9
[  401.742494] RIP: 0033:0x7f7ac12fce0d
[  401.742497] Code: 0f 1f 40 00 48 8b 15 a9 aa 0c 00 f7 d8 64 89 02 48 83 ec 08 e8 00 00 00 00 c9 c3 0f 1f 40 00 b8 00 00 00 00 0f 05 c3 <48> 8b 15 99 aa 0c 00 f7 d8 64 89 02 b8 00 00 00 00 c3 
[  401.742512] RSP: 002b:00007ffd44fa80d8 EFLAGS: 00000246 ORIG_RAX: 0000000000000000
[  401.742515] RAX: ffffffffffffffda RBX: 0000562d95fb0d40 RCX: 00007f7ac12fce0d
[  401.742518] RDX: 0000000000000010 RSI: 0000562d9601fc80 RDI: 0000000000000000
[  401.742520] RBP: 00007ffd44fa8120 R08: 0000000000000000 R09: 00007ffd44fa8020
[  401.742523] R10: 00007ffd44fa8130 R11: 0000000000000246 R12: 0000562d9601fc80
[  401.742526] R13: 0000000000000000 R14: 0000562d96020300 R15: 0000562d95fb0d40
[  401.742529] Modules linked in: i915 drm_kms_helper drm fb_sys_fops
[  401.742534] ---[ end trace 0cfeb2c4f5bca001 ]---
[  401.742537] RIP: __copy_to_user+0x3a/0x60
[  401.742540] Code: f0 ff ff 4c 89 f7 48 89 45 d8 e8 36 d4 ff ff 48 85 c0 74 11 48 8b 45 d8 4c 89 fe 48 89 c7 e8 4a 23 00 00 5d c3 0f 0b eb f0 <48> 89 3f c3 0f 1f 84 00 00 00 00 00 
[  401.742555] CR2: 0000000000000010
[  401.742558] Kernel panic - not syncing: Fatal exception in interrupt
[  401.742562] Kernel Offset: 0x21e000000 from 0xffffffff81000000 (relocation range: 0xffffffff80000000-0xffffffffbfffffff)
[  401.742566] ---[ end Kernel panic - not syncing: Fatal exception in interrupt ]---\n
"""
            self._log(panic)
            return 9999, panic # 9999 is a workaround for the way Python handles returns, this just signals to your handler to exit
        if self.fallback == 'subprocess':
            try:
                result = subprocess.run(command_line, shell=True, check=False, capture_output=True, text=True)
                self._log(f"bashshim: fallback_exec: exit {result.returncode}")
                return result.returncode, result.stdout + result.stderr
            except Exception as e:
                self._log(f"bashshim: subprocess fallback_exec error: {e}")
                return 139, f"Segmentation fault (core dumped)\n"
