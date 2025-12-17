import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';

import { RentarArticuloComponent } from './rentar/rentar-articulo.component';
import { RentaResumenComponent } from './resumen/renta-resumen.component';
import { MisRentasComponent } from './mis/mis-rentas.component';
import { InboxComponent } from './inbox/inbox.component';

@NgModule({
	declarations: [RentarArticuloComponent, RentaResumenComponent, MisRentasComponent, InboxComponent],
	imports: [CommonModule, ReactiveFormsModule],
	exports: [RentarArticuloComponent, RentaResumenComponent, MisRentasComponent, InboxComponent],
})
export class RentasModule {}

