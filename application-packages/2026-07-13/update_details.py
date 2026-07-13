from pathlib import Path

ROOT = Path('/home/ubuntu/careerpilot/application-packages/2026-07-13')

CANDIDATE = """CANDIDATE DETAILS (provided 13 Jul 2026)
- Name: Subham Hirani
- Email: subhamhirani001@gmail.com
- Phone: +91 98750 27571
- Location: Ahmedabad, India (willing to commute/relocate to Gandhinagar and GIFT City)
- LinkedIn: https://www.linkedin.com/in/subham-hirani/
- Current CTC: Rs 12,500/month + performance-based incentive
- Expected CTC: Rs 20,000/month
- Notice period: Immediate joining (0 days)
- Work authorization: Authorized to work in India
"""

ROLES = {
    "01_system_administrator_gandhinagar": ("System Administrator - Windows/Linux Server", "Big Ideas Social Media Recruitment", "Gandhinagar, Gujarat", "https://www.shine.com/jobs/system-administrator-windows-linux-server/big-ideas-social-media-recruitment/19188395", "Shine Apply (requires Shine login)"),
    "02_support_system_engineer_gandhinagar": ("Support System Engineer - Windows/Linux Server", "Big Ideas Social Media Recruitment", "Gandhinagar, Gujarat", "https://www.shine.com/jobs/support-system-engineer-windows-linux-server/big-ideas-social-media-recruitment/19185040", "Shine Apply (requires Shine login)"),
    "03_support_engineer_synoptek_ahmedabad": ("Support Engineer I", "Synoptek", "Ahmedabad, Gujarat", "https://www.shine.com/jobs/support-engineer-i/synoptek/19167161", "Synoptek careers portal: https://careers.synoptek.com/jobs"),
    "04_network_security_engineer_aeromesh_ahmedabad": ("Senior Network & Security Engineer", "Aeromesh Systems", "Ahmedabad, Gujarat", "https://www.shine.com/jobs/senior-network-security-engineer/aeromesh-systems/19184316", "Aeromesh official careers: https://aeromeshsystems.com/careers/  (NOTE: lists 4+ yrs; see honest-inquiry approach)"),
    "05_cisco_network_engineer_sndk_ahmedabad": ("Cisco Network Engineer", "SNDK Corp", "Ahmedabad, Gujarat", "https://www.shine.com/jobs/cisco-network-engineer/sndk-corp/19206495", "Cold email: careers@sndkcorp.com"),
    "06_network_engineer_l2_gift_city": ("Network Engineer L2", "Talent Vision Services", "GIFT City / Ahmedabad, Gujarat", "https://www.shine.com/jobs/network-engineer-l2-gift-city-ahmedabad/talent-vision-services/19098154", "Cold email: info@talentvisionservices.com"),
}

for slug, (title, company, loc, url, channel) in ROLES.items():
    d = ROOT / slug
    d.mkdir(parents=True, exist_ok=True)
    content = f"""ROLE: {title}
COMPANY: {company}
LOCATION: {loc}
POSTING URL: {url}
SUBMISSION CHANNEL: {channel}

{CANDIDATE}
STATUS: Prepared - pending submission (see gate below)
GATE: Authenticated Shine/LinkedIn/company-portal apply requires the candidate's login + OTP/CAPTCHA. Cold emails require a configured sending mailbox.
"""
    (d / "application_details.txt").write_text(content, encoding="utf-8")

print("Updated 6 application_details.txt files with candidate details.")
