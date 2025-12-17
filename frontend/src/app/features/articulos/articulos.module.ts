import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';

import { ListadoArticulosComponent } from './listado/listado-articulos.component';
import { PublicarArticuloComponent } from './publicar/publicar-articulo.component';
import { EditarArticuloComponent } from './editar/editar-articulo.component';
import { DetalleArticuloComponent } from './detalle/detalle-articulo.component';

@NgModule({
  declarations: [
    ListadoArticulosComponent,
    PublicarArticuloComponent,
    EditarArticuloComponent,
    DetalleArticuloComponent,
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
  ],
  exports: [
    ListadoArticulosComponent, // para que AppRouting pueda usarlo en las rutas
    PublicarArticuloComponent,
    EditarArticuloComponent,
    DetalleArticuloComponent,
  ],
})
export class ArticulosModule {}
