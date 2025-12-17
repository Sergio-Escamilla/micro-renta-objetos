import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { RentaService } from 'src/app/core/services/renta.service';
import { RentaResumen } from 'src/app/core/models/renta.model';
import { AuthService } from 'src/app/core/services/auth.service';

@Component({
  selector: 'app-mis-rentas',
  templateUrl: './mis-rentas.component.html',
  styleUrls: ['./mis-rentas.component.scss'],
})
export class MisRentasComponent implements OnInit {
  loading = false;
  errorMessage = '';

  rentas: RentaResumen[] = [];

  constructor(
    private readonly router: Router,
    private readonly rentaService: RentaService,
    private readonly authService: AuthService
  ) {}

  ngOnInit(): void {
    this.cargar();
  }

  volverExplorar(): void {
    this.router.navigate(['/explorar']);
  }

  verResumen(r: RentaResumen): void {
    const id = r.id_renta ?? r.id;
    this.router.navigate(['/rentas/resumen', id]);
  }

  private cargar(): void {
    this.loading = true;
    this.errorMessage = '';

    this.rentaService.listarMisRentas('arrendatario').subscribe({
      next: (items) => {
        this.rentas = items;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        const status = err?.status;
        const hasToken = !!this.authService.getToken();
        if ((status === 401 || status === 422) && !hasToken) {
          this.router.navigate(['/login']);
          return;
        }
        this.errorMessage = err?.error?.message || 'No se pudieron cargar tus rentas.';
      },
    });
  }
}
