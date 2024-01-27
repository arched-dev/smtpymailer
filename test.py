from dotenv import load_dotenv

from smtpymailer import SmtpMailer

load_dotenv()

mailer = SmtpMailer(sender_email="charles@colemanbros.co.uk", sender_name="Charles Maurice")
mailer.send_email(["lewis@arched.dev", "lewis.morris@gmail.com"], "CID TEST50 Coleman's Credit Note 2dfffd", alter_img_src="cid", cc_recipients="chris@colemanbros.co.uk", attachments=["~/Downloads/test_inv.pdf"], template="./test_email.html", name="Lewis", email="charlie@colemanbros.co.uk", website="colemanbros.co.uk", address="50 dog rd, cheeseville, CH3 SSE", invoice=2658555)
