import json

data = json.load(open('scan_config_debug.json'))
creds = data['credentials']['data']
host = [c for c in creds if c['name']=='Host'][0]
ssh = [t for t in host['types'] if 'SSH' in t['name']][0]

# Get password auth option which contains escalation field
auth_field = [i for i in ssh['inputs'] if i['id']=='auth_method'][0]
print("Auth method options:")
for opt in auth_field.get('options', []):
    if isinstance(opt, dict):
        print(f"  - {opt.get('name')}")
    else:
        print(f"  - {opt}")

print("\n" + "="*60)

# Get escalation options from password auth
password_opt = [o for o in auth_field['options'] if isinstance(o, dict) and o.get('name') == 'password'][0]
escalation_field = [i for i in password_opt['inputs'] if i['id'] == 'elevate_privileges_with'][0]

print(f"\nEscalation type: {escalation_field['type']}")
print("Escalation options:")
for opt in escalation_field.get('options', []):
    if isinstance(opt, dict):
        print(f"  - {opt.get('name')}")
    else:
        print(f"  - {opt}")
