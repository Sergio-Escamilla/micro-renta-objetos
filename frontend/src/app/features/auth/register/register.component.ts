import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
})
export class RegisterComponent {
  form: FormGroup;
  loading = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.form = this.fb.group({
      nombre: ['', Validators.required],
      apellidos: ['', Validators.required],
      correo_electronico: ['', [Validators.required, Validators.email]],
      contrasena: ['', [Validators.required, Validators.minLength(6)]],
    });
  }

  onSubmit(): void {
    if (this.form.invalid || this.loading) return;

    this.loading = true;
    this.errorMessage = '';

    const payload = this.form.value;

    this.authService.register(payload).subscribe({
      next: (resp) => {
        this.loading = false;
        if (resp.success) {
          this.router.navigate(['/login']);
          return;
        }
        this.errorMessage = resp.message || 'No se pudo registrar.';
      },
      error: (err) => {
        console.error('Error en registro', err);
        this.loading = false;
        this.errorMessage = 'Error al registrar. Revisa tus datos.';
      },
    });
  }
}
