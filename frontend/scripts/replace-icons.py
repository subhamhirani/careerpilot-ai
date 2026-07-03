#!/usr/bin/env python3
"""
Replace lucide-react imports with phosphor-icons.
Maps common lucide icons to their phosphor equivalents.
"""

import os
import re
import glob

# Icon mapping from lucide-react to phosphor-icons/react
ICON_MAP = {
    # Common icons with same names
    'Send': 'Send',
    'Clock': 'Clock',
    'CheckCircle': 'CheckCircle',
    'XCircle': 'XCircle',
    'AlertCircle': 'WarningCircle',
    'Building2': 'Building',
    'MapPin': 'MapPin',
    'FileText': 'FileText',
    'Menu': 'List',
    'Bell': 'Bell',
    'Rocket': 'Rocket',
    'LogOut': 'SignOut',
    'User': 'User',
    'Moon': 'Moon',
    'Sun': 'Sun',
    'Monitor': 'Monitor',
    'Save': 'Save',
    'Plus': 'Plus',
    'Trash2': 'Trash',
    'Settings': 'Gear',
    'Search': 'MagnifyingGlass',
    'Shield': 'ShieldCheck',
    'Key': 'Key',
    'Eye': 'Eye',
    'EyeOff': 'EyeSlash',
    'Loader2': 'Spinner',
    'Briefcase': 'Briefcase',
    'CheckSquare': 'CheckboxChecked',
    'Calendar': 'Calendar',
    'ExternalLink': 'ArrowSquareOut',
    'TrendingUp': 'TrendUp',
    'TrendingDown': 'TrendDown',
    'Minus': 'Minus',
    'Star': 'Star',
    'Download': 'Download',
    'Upload': 'Upload',
    'RefreshCw': 'ClockwiseRotation',
    'UserCircle': 'UserCircle',
    'Github': 'GithubLogo',
    'Linkedin': 'LinkedinLogo',
    'Globe': 'Globe',
    'X': 'X',
    'AlertTriangle': 'Warning',
}

def replace_imports(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    
    # Replace lucide-react import with phosphor-icons/react
    content = re.sub(
        r"from ['\"]lucide-react['\"]",
        "from 'phosphor-icons/react'",
        content
    )
    
    # Replace individual icon imports
    # Match: import { Icon1, Icon2, Icon3 } from 'lucide-react'
    pattern = r"import\s*{\s*([^}]+)\s*}from\s*['\"]lucide-react['\"]"
    
    def replace_icon(match):
        icons_str = match.group(1)
        icons = [i.strip() for i in icons_str.split(',')]
        new_icons = []
        for icon in icons:
            if icon in ICON_MAP:
                new_icons.append(ICON_MAP[icon])
            else:
                new_icons.append(icon)
        return f"import {{ {', '.join(new_icons)} }} from 'phosphor-icons/react'"
    
    content = re.sub(pattern, replace_icon, content)
    
    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

# Find all TSX/TS files
files = glob.glob('/home/ubuntu/careerpilot/frontend/src/**/*.tsx', recursive=True)
files += glob.glob('/home/ubuntu/careerpilot/frontend/src/**/*.ts', recursive=True)

changed = 0
for f in files:
    if replace_imports(f):
        print(f"✓ {f}")
        changed += 1

print(f"\n{changed} files updated")