import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { DashboardComponent } from './dashboard/dashboard.component';
import { AdminIncidentesComponent } from './incidentes/admin-incidentes.component';
import { AdminUsuariosComponent } from './usuarios/admin-usuarios.component';
import { AdminArticulosComponent } from './articulos/admin-articulos.component';
import { AdminPuntosEntregaComponent } from './puntos-entrega/admin-puntos-entrega.component';

@NgModule({
	declarations: [
		DashboardComponent,
		AdminIncidentesComponent,
		AdminUsuariosComponent,
		AdminArticulosComponent,
		AdminPuntosEntregaComponent,
	],
	imports: [CommonModule, FormsModule, RouterModule],
})
export class AdminModule {}
