"""Send the two authorized cold-email applications via Gmail SMTP.

Uses the candidate-provided Gmail app password (spaces stripped).
Sends:
  1) SNDK Corp - Cisco Network Engineer -> careers@sndkcorp.com
  2) Talent Vision Services - Network Engineer L2 GIFT City -> info@talentvisionservices.com
"""
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

ROOT = Path("/home/ubuntu/careerpilot/application-packages/2026-07-13")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
FROM = "subhamhirani001@gmail.com"
APP_PASS = "arol cswc ekzj lsvn".replace(" ", "")

CANDIDATE_SIG = (
    "Subham Hirani\n"
    "Ahmedabad, India | +91 98750 27571 | subhamhirani001@gmail.com\n"
    "LinkedIn: https://www.linkedin.com/in/subham-hirani/"
)

APPLICATIONS = [
    {
        "to": "careers@sndkcorp.com",
        "subject": "Application - Cisco Network Engineer | Subham Hirani",
        "body": (
            "Dear SNDK Hiring Team,\n\n"
            "I am applying for the Cisco Network Engineer opening in Ahmedabad. I currently work as a "
            "Network & Infrastructure Engineer, where I have configured multi-ISP RRAS redundancy, "
            "administered Windows Server 2025 with AD DS/DNS/DHCP/GPO, supported LAN/WAN incidents, and "
            "maintained operational runbooks and firewall matrices.\n\n"
            "My full-time CCNA-focused training covered TCP/IP, VLANs, OSPF, ACLs, NAT/PAT, STP, and "
            "routing/switching troubleshooting. I am particularly interested in SNDK because of its work in "
            "networking and security, virtualization, Linux/open-source systems, and cloud infrastructure.\n\n"
            "I have attached a role-tailored CV and cover letter. I would appreciate the opportunity to "
            "discuss how I can contribute to your network and security team.\n\n"
            "Regards,\n" + CANDIDATE_SIG
        ),
        "attachments": [
            ROOT / "05_cisco_network_engineer_sndk_ahmedabad" / "Subham_Hirani_Tailored_CV.docx",
            ROOT / "05_cisco_network_engineer_sndk_ahmedabad" / "Subham_Hirani_Cover_Letter.docx",
        ],
    },
    {
        "to": "info@talentvisionservices.com",
        "subject": "Application - Network Engineer L2, GIFT City / Ahmedabad | Subham Hirani",
        "body": (
            "Dear Talent Vision Services Team,\n\n"
            "I am writing to apply for the Network Engineer L2 opportunity for GIFT City / Ahmedabad. My "
            "current role as a Network & Infrastructure Engineer includes multi-ISP RRAS network "
            "configuration, Windows Server and Active Directory administration, LAN/WAN troubleshooting, "
            "firewall hardening, Docker-hosted GitLab operations, and automated backup/DR implementation.\n\n"
            "I am based in Ahmedabad and willing to work in GIFT City. My hands-on CCNA routing-and-switching "
            "training and production infrastructure work have built a practical foundation in routers, "
            "switches, VLANs, routing, security, troubleshooting, and documentation.\n\n"
            "My tailored CV and cover letter are attached. I would welcome the opportunity to be considered "
            "or to be connected with the end client's hiring team.\n\n"
            "Regards,\n" + CANDIDATE_SIG
        ),
        "attachments": [
            ROOT / "06_network_engineer_l2_gift_city" / "Subham_Hirani_Tailored_CV.docx",
            ROOT / "06_network_engineer_l2_gift_city" / "Subham_Hirani_Cover_Letter.docx",
        ],
    },
]


def send_one(app):
    msg = EmailMessage()
    msg["From"] = FROM
    msg["To"] = app["to"]
    msg["Subject"] = app["subject"]
    msg.set_content(app["body"])
    for path in app["attachments"]:
        if not path.exists():
            raise FileNotFoundError(f"Missing attachment: {path}")
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=path.name,
        )
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(FROM, APP_PASS)
        server.send_message(msg)
    return f"Sent -> {app['to']} subject='{app['subject']}'"


if __name__ == "__main__":
    results = []
    for app in APPLICATIONS:
        try:
            results.append(send_one(app))
        except Exception as e:  # surface real failure, do not fake success
            results.append(f"FAILED -> {app['to']}: {type(e).__name__}: {e}")
    print("\n".join(results))
