## Install

### Create venv
```shell
python3 -m venv ~/odoo-ven
```

### Active venv
```shell
source ~/odoo-venv/bin/activate
```

### Pip Upgrade
```shell
pip install --upgrade pip setuptools wheel
```

### Pip install requirements
```shell
pip install -r requirements.txt
```


### psycopg2 and python-ldap system-level development libraries
```shell
apt install -y libpq-dev libsasl2-dev python3-dev libldap2-dev libssl-dev build-essential
```

### odoo.conf
```pycon
[options]

; Database settings
db_host = localhost
db_port = 5432
db_user = forge
db_password = uIkXs1ynXC6uOyYmAanC
db_name = odoo_db
```

### start-odoo.sh
```shell
#!/bin/bash
source ~/odoo-venv/bin/activate
exec ./odoo-bin -c odoo.conf
```
```shell
chmod +x start-odoo.sh
```

## odoo-bin
```python
#!/usr/bin/env python3

# set server timezone in UTC before time module imported
__import__('os').environ['TZ'] = 'UTC'
import odoo

if __name__ == "__main__":
    odoo.cli.main()
```
```shell
chmod +x odoo-bin
```

