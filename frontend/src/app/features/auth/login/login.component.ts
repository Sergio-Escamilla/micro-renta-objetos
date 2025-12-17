import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  loginForm: FormGroup;
  loading = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.loginForm = this.fb.group({
      correo_electronico: ['', [Validators.required, Validators.email]],
      contrasena: ['', [Validators.required, Validators.minLength(4)]],
    });
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.loading) {
      return;
    }

    this.loading = true;
    this.errorMessage = '';

    const { correo_electronico, contrasena } = this.loginForm.value;

    this.authService.login(correo_electronico, contrasena).subscribe({
      next: (resp) => {
        console.log('Login OK', resp);

        this.loading = false;

        // Aquí ya se guardó el token en el AuthService (localStorage)
        // Redirigimos a la siguiente pantalla (ajusta la ruta a lo que quieras)
        this.router.navigate(['/explorar']);
      },
      error: (err) => {
        console.error('Error en login', err);
        this.loading = false;
        this.errorMessage = 'Error al iniciar sesión. Verifica tus datos.';
      },
    });
  }
}
