/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef PITIVI_EFFECTSWINDOW_H
#define PITIVI_EFFECTSWINDOW_H

/*
 * Potentially, include other headers on which this header depends.
 */

/*
 * Type macros.
 */

#define PITIVI_EFFECTSWINDOW_TYPE (pitivi_effectswindow_get_type ())
#define PITIVI_EFFECTSWINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_EFFECTSWINDOW_TYPE, PitiviEffectsWindow))
#define PITIVI_EFFECTSWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_EFFECTSWINDOW_TYPE, PitiviEffectsWindowClass))
#define PITIVI_IS_EFFECTSWINDOW(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_EFFECTSWINDOW_TYPE))
#define PITIVI_IS_EFFECTSWINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_EFFECTSWINDOW_TYPE))
#define PITIVI_EFFECTSWINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_EFFECTSWINDOW_TYPE, PitiviEffectsWindowClass))

typedef struct _PitiviEffectsWindow PitiviEffectsWindow;
typedef struct _PitiviEffectsWindowClass PitiviEffectsWindowClass;
typedef struct _PitiviEffectsWindowPrivate PitiviEffectsWindowPrivate;
typedef struct _PitiviTreeModel PitiviTreeModel;

struct _PitiviTreeModel
{
  GtkWidget *label;
  GtkWidget *treeview;
  GtkWidget *scroll;
};

struct _PitiviEffectsWindow
{
  GtkWindow parent;

  /* instance public members */

  /* private */
  PitiviEffectsWindowPrivate *private;
};

struct _PitiviEffectsWindowClass
{
  GtkWindowClass parent;
  /* class members */
};

/* used by PITIVI_EFFECTSWINDOW_TYPE */
GType pitivi_effectswindow_get_type (void);

/*
 * Method definitions.
 */

PitiviEffectsWindow	*pitivi_effectswindow_new(void);

#endif
