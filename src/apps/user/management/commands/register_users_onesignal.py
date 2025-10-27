from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.user.utils import register_user_with_onesignal

User = get_user_model()


class Command(BaseCommand):
    help = 'Register existing users with OneSignal for push notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Register a specific user by ID',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of users to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually registering users',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('OneSignal User Registration Command')
        )

        if options['user_id']:
            # Register a specific user
            try:
                user = User.objects.get(id=options['user_id'])
                self.register_single_user(user, options['dry_run'])
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {options["user_id"]} not found')
                )
        else:
            # Register all users
            self.register_all_users(options['batch_size'], options['dry_run'])

    def register_single_user(self, user, dry_run=False):
        """Register a single user with OneSignal"""
        self.stdout.write(f'Processing user: {user} (ID: {user.id})')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would register user {user.id} with OneSignal')
            )
            return

        result = register_user_with_onesignal(user)

        if result['success']:
            if result['error_type'] == 'acceptable':
                self.stdout.write(
                    self.style.SUCCESS(f'✅ User {user.id} already registered')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully registered user {user.id}')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to register user {user.id}: {result["error_message"]}')
            )

    def register_all_users(self, batch_size, dry_run=False):
        """Register all users with OneSignal in batches"""
        total_users = User.objects.count()
        self.stdout.write(f'Found {total_users} users to process')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would register {total_users} users with OneSignal')
            )
            return

        processed = 0
        successful = 0
        failed = 0

        # Process users in batches
        for start in range(0, total_users, batch_size):
            end = min(start + batch_size, total_users)
            users_batch = User.objects.all()[start:end]

            self.stdout.write(f'Processing batch {start + 1}-{end} of {total_users}')

            for user in users_batch:
                result = register_user_with_onesignal(user)
                processed += 1

                if result['success']:
                    successful += 1
                    if result['error_type'] == 'acceptable':
                        self.stdout.write(f'✅ User {str(user)} already registered')
                    else:
                        self.stdout.write(f'✅ User {str(user)} registered successfully')
                else:
                    failed += 1
                    self.stdout.write(f'❌ User {str(user)} registration failed: {result["error_message"]}')

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Registration Summary ===\n'
                f'Total processed: {processed}\n'
                f'Successful: {successful}\n'
                f'Failed: {failed}\n'
            )
        )
