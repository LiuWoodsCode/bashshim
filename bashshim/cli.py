from .shell import BashShim
import argparse
import sys
def main():
    parser = argparse.ArgumentParser(description="Fake Bash shell simulator")
    parser.add_argument('--fallback', default='error', help='Fallback mode for unknown commands (default: error)')
    parser.add_argument('--os-flavor', default='Linux', help='Simulated OS flavor (Linux, Darwin, BSD)')
    parser.add_argument('--username', default='inkling', help='Username')
    parser.add_argument('--uid', type=int, default=1337, help='User ID')
    parser.add_argument('--distro-name', default='FakeOS', help='Distribution name')
    parser.add_argument('--distro-codename', default='marie', help='Distribution codename')
    parser.add_argument('--distro-id', default='fakeos', help='Distribution ID')
    parser.add_argument('--distro-version', default='1.0', help='Distribution version')
    # Parse known args to get os_flavor before setting kernel-version default
    partial_args, _ = parser.parse_known_args()
    os_flavor = partial_args.os_flavor
    if os_flavor.lower() == 'linux':
        kernel_default = '6.0'
    elif os_flavor.lower() == 'darwin':
        kernel_default = '23.0.0'
    elif os_flavor.lower() == 'bsd':
        kernel_default = '14.0'
    else:
        kernel_default = '6.0'
    parser.add_argument('--kernel-version', default=kernel_default, help='Kernel version')
    parser.add_argument('--package-manager', default='apt', help='Package manager name')
    parser.add_argument('--package-manager-mirror', default='http://package.fakeos.org', help='Package manager mirror URL')
    parser.add_argument('--allow-networking', action='store_true', help='Allow networking commands (curl, wget, etc.)')
    parser.add_argument('--log-dmesg', action='store_true', help='Enable dmesg logging')
    parser.add_argument('-c', '--command', help='Run a single command and exit')
    args = parser.parse_args()

    shim = BashShim(
        fallback=args.fallback,
        os_flavor=args.os_flavor,
        username=args.username,
        uid=args.uid,
        distro_name=args.distro_name,
        distro_codename=args.distro_codename,
        distro_id=args.distro_id,
        distro_version=args.distro_version,
        package_manager=args.package_manager,
        package_manager_mirror=args.package_manager_mirror,
        log_dmesg=args.log_dmesg,
        allow_networking=args.allow_networking,
        kernel_version=args.kernel_version
    )

    if args.command:
        code, out = shim.run(args.command)
        print(out, end='')
        exit(code)

    # print(f"Fake shell ready. Logged in as: {shim.username} ({shim.sim_os})")
    while True:
        try:
            # Show the fake cwd relative to the fake root, always starting with '/'
            fake_cwd = '/' + str(shim.cwd.relative_to(shim.fakeroot)).replace('\\', '/')
            cmd = input(f'{shim.username}@{shim.hostname}:{fake_cwd} $ ')
            try:
                code, out = shim.run(cmd)
            except Exception as e:
                code = 1
                out = f"Error: {str(e)}\n"
            print(out, end='')
            if code == 9999:
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\n[exit]")
            break
