from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Seed initial demonstration accounts for Brightloop (Admin, Staff, Customer)"

    def handle(self, *args, **options):
        # 1. System Admin
        admin_email = "admin@brightloop.com"
        admin_pass = "BrightAdmin123!"
        if not User.objects.filter(email=admin_email).exists():
            admin_user = User.objects.create_superuser(
                email=admin_email,
                password=admin_pass,
                first_name="Admin",
                last_name="User",
                company_name="Brightloop Software HQ",
                role=User.Role.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f"Created Admin: {admin_email} / {admin_pass}"))
        else:
            self.stdout.write(f"Admin {admin_email} already exists.")

        # 2. Internal Staff
        staff_email = "sarah.sales@brightloop.com"
        staff_pass = "BrightStaff123!"
        if not User.objects.filter(email=staff_email).exists():
            staff_user = User.objects.create_user(
                email=staff_email,
                password=staff_pass,
                first_name="Sarah",
                last_name="Jenkins",
                company_name="Brightloop Operations",
                phone="+1 (555) 234-5678",
                role=User.Role.STAFF,
                is_staff=True
            )
            self.stdout.write(self.style.SUCCESS(f"Created Staff: {staff_email} / {staff_pass}"))
        else:
            self.stdout.write(f"Staff {staff_email} already exists.")

        # 3. Customer 1 (Acme Shop)
        cust_email = "john@acmeshop.com"
        cust_pass = "AcmeCustomer123!"
        if not User.objects.filter(email=cust_email).exists():
            cust_user = User.objects.create_user(
                email=cust_email,
                password=cust_pass,
                first_name="John",
                last_name="Doe",
                company_name="Acme Retail Shop",
                phone="+1 (555) 987-6543",
                address="123 Market St, Suite 400, Austin, TX",
                role=User.Role.CUSTOMER
            )
            self.stdout.write(self.style.SUCCESS(f"Created Customer: {cust_email} / {cust_pass}"))
        else:
            self.stdout.write(f"Customer {cust_email} already exists.")

        # 4. Customer 2 (MegaCorp)
        mega_email = "lisa@megacorp.com"
        mega_pass = "MegaCorp123!"
        if not User.objects.filter(email=mega_email).exists():
            mega_user = User.objects.create_user(
                email=mega_email,
                password=mega_pass,
                first_name="Lisa",
                last_name="Vance",
                company_name="MegaCorp Enterprise",
                phone="+1 (555) 432-1098",
                address="500 Tech Blvd, 12th Floor, San Francisco, CA",
                role=User.Role.CUSTOMER
            )
            self.stdout.write(self.style.SUCCESS(f"Created Customer: {mega_email} / {mega_pass}"))
        else:
            self.stdout.write(f"Customer {mega_email} already exists.")
