# Coworking Space Addon Installation Guide

## 🚨 Troubleshooting "Cancel Install" Error

### Step 1: Check Odoo Server Logs
The "Cancel Install" error usually means there's an underlying issue. Check your Odoo server logs:

```bash
# If running Odoo from command line, check the terminal output
# If using systemd service:
sudo journalctl -u odoo -f

# If using log files:
tail -f /var/log/odoo/odoo.log
```

### Step 2: Restart Odoo Server
```bash
# If running from command line, stop with Ctrl+C and restart:
./odoo-bin -c /path/to/your/config.conf

# If using systemd:
sudo systemctl restart odoo

# If using Docker:
docker restart your-odoo-container
```

### Step 3: Update Apps List
1. Go to Apps menu in Odoo
2. Click "Update Apps List" button
3. Wait for the update to complete
4. Search for "Coworking Space Management"

### Step 4: Check Dependencies
Ensure all required modules are installed:

**Required modules:**
- base ✅ (always available)
- website ✅ (usually available)
- sale ✅ (usually available)
- account ✅ (usually available)
- crm ✅ (usually available)
- portal ✅ (usually available)
- calendar ✅ (usually available)
- product ✅ (usually available)

**Optional modules (commented out in manifest):**
- website_sale
- website_event
- website_payment
- sale_subscription
- event
- payment
- stock

### Step 5: Install in Developer Mode
1. Enable Developer Mode: Settings → Activate Developer Mode
2. Go to Apps → Update Apps List
3. Remove "Apps" filter to see all modules
4. Search for "Coworking Space Management"
5. Try installing again

### Step 6: Manual Installation via Command Line
If UI installation fails, try command line:

```bash
# Navigate to Odoo directory
cd /path/to/odoo

# Install the addon
./odoo-bin -d your_database_name -i coworking_space --stop-after-init

# Or update if already partially installed
./odoo-bin -d your_database_name -u coworking_space --stop-after-init
```

### Step 7: Check Database Permissions
Ensure your Odoo user has proper database permissions:

```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Grant permissions to Odoo user
GRANT ALL PRIVILEGES ON DATABASE your_database_name TO your_odoo_user;
GRANT CREATE ON SCHEMA public TO your_odoo_user;
```

### Step 8: Common Error Solutions

#### Error: "Module not found"
- Ensure the addon is in the correct addons path
- Check that the path is included in Odoo configuration

#### Error: "Dependency not found"
- Install missing dependencies first
- Or comment out optional dependencies in __manifest__.py

#### Error: "Permission denied"
- Check file permissions: `chmod -R 755 odoo/addons/coworking_space`
- Ensure Odoo user can read the files

#### Error: "Database constraint violation"
- Drop and recreate the database if in development
- Or use `--update=all` flag

### Step 9: Minimal Installation Test
If still failing, try installing with minimal features:

1. Edit `__manifest__.py` and comment out all data files except security
2. Try installing with just the models
3. Gradually add back features

### Step 10: Get Detailed Error Information

Add this to your Odoo configuration file:
```ini
[options]
log_level = debug
log_handler = :DEBUG
```

Or run Odoo with verbose logging:
```bash
./odoo-bin -d your_db --log-level=debug -i coworking_space --stop-after-init
```

## 🎯 Quick Fix Commands

```bash
# 1. Restart Odoo (if using systemd)
sudo systemctl restart odoo

# 2. Update apps list via command line
./odoo-bin -d your_db --update=base --stop-after-init

# 3. Force install the addon
./odoo-bin -d your_db -i coworking_space --stop-after-init

# 4. Check addon is in the right place
ls -la odoo/addons/coworking_space/

# 5. Verify Python syntax
python3 -m py_compile odoo/addons/coworking_space/__init__.py
```

## 📞 Still Having Issues?

If you're still getting "Cancel Install" after trying these steps:

1. **Share the exact error message** from Odoo server logs
2. **Check your Odoo version** - ensure it's compatible with 18.0
3. **Verify addon path** - make sure it's in the correct addons directory
4. **Try a fresh database** - create a new database and test installation

The addon has been tested and all files are valid, so the issue is likely environmental or configuration-related.
