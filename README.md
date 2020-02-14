# tpcrontools

- [cronctl](#cronctl) - Add or remove jobs from user's crontab

## cronctl

```
usage: cronctl [-h] (--list | --add TYPE | --remove) [-f] path [path ...]

Tool for manage jobs in crontab

positional arguments:
  path         Path to folder with job scripts

optional arguments:
  -h, --help   show this help message and exit
  --list       List all robots sorted by type
  --add TYPE   Add jobs of the appropriate type from the specified path
  --remove     Remove all jobs with given path
  -f, --force  Store changes into crontab without confirmation

Example of job file header:
  #!/usr/bin/env bash

  #PT:cron:10 1,2,3,4 * * *
  #PDI:cron:40 5,6,7,8 * * *

With this example "cronctl --add I /robots/scripts" adds to the current user's crontab row:
40 5,6,7,8 * * * /robots/scripts/example.sh
```

For example, if you want to add production jobs from folder /opt/robots
```
  cronctl --add P /opt/robots
```

if we want to uninstall all jobs from folder /opt/alpha/robots (because our application moves from alpha to beta stage):
```
  cronctl -f --remove /opt/alpha/robots
```

