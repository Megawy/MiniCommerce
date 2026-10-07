import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { FieldErrors, apiErrorMessage, fieldErrors } from '../../../core/http/api-error';
import { Alert } from '../../../shared/ui/alert';

@Component({
  selector: 'mc-register',
  imports: [ReactiveFormsModule, RouterLink, Alert],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './register.html',
  styleUrl: '../auth-page.css',
})
export class Register {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  /** Validation messages returned by Django (e.g. "A user with this email already exists."). */
  protected readonly serverErrors = signal<FieldErrors>({});

  protected readonly form = inject(NonNullableFormBuilder).group({
    first_name: [''],
    last_name: [''],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.error.set(null);
    this.serverErrors.set({});
    this.auth.register(this.form.getRawValue()).subscribe({
      next: () => void this.router.navigateByUrl('/'),
      error: (err) => {
        const fields = fieldErrors(err);
        this.serverErrors.set(fields);
        if (Object.keys(fields).length === 0) this.error.set(apiErrorMessage(err));
        this.submitting.set(false);
      },
    });
  }
}
