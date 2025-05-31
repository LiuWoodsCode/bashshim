# BashShim
> [!IMPORTANT]
> The docs are currently incomplete. Contributions are welcome!

BashShim is a simulator for the Bourne shell. While it can be used as a shell using fakeroot-shell, it's primary use is to be used as a fake operating enviorment for forms of agentic AI that require a shell.
## Why use this rather than a sandbox like E2B or a container?
One main advantage of BashShim is that it allows you to run it locally, avoiding the cost of an API, and have full control over the simulated system. As it's just a recreation of Bash written in Python, it takes up way less compute resources than even containers!
## So, is this the replacement to LiuOS?
No. At least not right now. LiuOS is more focused on being a simulation of an OS and not a full REPL.
