import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty, EnumProperty
import bmesh
from .. utils.graph import build_mesh_graph
from .. utils.bmesh import ensure_custom_data_layers
from .. utils.selection import get_sweeps_from_fillet, get_2_rails_from_chamfer
from .. utils.sweep import debug_sweeps
from .. utils.tool import unfuse, set_rail_sharps_and_bweights
from .. utils.ui import popup_message, draw_init, draw_title, draw_prop, init_cursor, wrap_cursor, update_HUD_location
from .. utils.ui import init_status, finish_status
from .. utils.draw import vert_debug_print
from .. utils.developer import output_traceback
from .. utils.registration import get_addon

class Unfuse(bpy.types.Operator):
    bl_idname = "machin3.unfuse"
    bl_label = "MACHIN3: Unfuse"
    bl_description = "Reconstruct Chamfer from Fillet/rounded Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    sharps: BoolProperty(name="Set Sharps", default=True)
    bweights: BoolProperty(name="Set Bevel Weights", default=False)
    bweight: FloatProperty(name="Weight", default=1, min=0, max=1)
    cyclic: BoolProperty(name="Cyclic", default=False)
    def draw(self, context):
        layout = self.layout
        column = layout.column()

        column.prop(self, "sharps")

        row = column.row()
        row.prop(self, "bweights")
        row.prop(self, "bweight")

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            draw_title(self, "Unfuse")

            draw_prop(self, "Set Sharps", self.sharps, hint="toggle S")
            draw_prop(self, "Set BWeights", self.bweights, offset=18, hint="toggle B")
            if self.bweights:
                draw_prop(self, "BWeight", self.bweight, offset=18, hint="ALT scroll UP/DOWN")

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(context.active_object.data)
            return len([f for f in bm.faces if f.select]) >= 1

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            update_HUD_location(self, event)

        events = ['WHEELUPMOUSE', 'UP_ARROW', 'ONE', 'WHEELDOWNMOUSE', 'DOWN_ARROW', 'TWO', 'S', 'B']

        if event.type in events:

            if event.type in {'WHEELUPMOUSE', 'UP_ARROW', 'ONE'} and event.value == 'PRESS':
                if event.alt:
                    self.bweight += 0.1

            elif event.type in {'WHEELDOWNMOUSE', 'DOWN_ARROW', 'TWO'} and event.value == 'PRESS':
                if event.alt:
                    self.bweight -= 0.1

            elif event.type == 'S' and event.value == "PRESS":
                self.sharps = not self.sharps

            elif event.type == 'B' and event.value == "PRESS":
                self.bweights = not self.bweights

            try:
                ret = self.main(self.active, modal=True)

                if not ret:
                    self.finish()
                    return {'FINISHED'}
            except Exception as e:
                self.finish()

                if bpy.context.mode == 'OBJECT':
                    bpy.ops.object.mode_set(mode='EDIT')

                output_traceback(self, e)
                return {'FINISHED'}

        elif event.type in {'MIDDLEMOUSE'} or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}) or event.type.startswith('NDOF'):
            return {'PASS_THROUGH'}

        elif event.type in {'LEFTMOUSE', 'SPACE'}:
            self.finish()
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_modal()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

    def cancel_modal(self, removeHUD=True):
        if removeHUD:
            self.finish()

        bpy.ops.object.mode_set(mode='OBJECT')
        self.initbm.to_mesh(self.active.data)
        bpy.ops.object.mode_set(mode='EDIT')

    def invoke(self, context, event):
        self.active = context.active_object

        self.active.update_from_editmode()

        self.init = True
        self.decalmachine = get_addon("DECALmachine")[0]

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)

        init_cursor(self, event)

        try:
            ret = self.main(self.active, modal=True)

            if not ret:
                self.cancel_modal(removeHUD=False)
                return {'FINISHED'}
        except Exception as e:
            if bpy.context.mode == 'OBJECT':
                bpy.ops.object.mode_set(mode='EDIT')

            output_traceback(self, e)
            return {'FINISHED'}

        init_status(self, context, 'Unfuse')

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        active = context.active_object

        try:
            self.main(active)
        except Exception as e:
            output_traceback(self, e)

        return {'FINISHED'}

    def main(self, active, modal=False):
        debug = True
        debug = False

        bpy.ops.object.mode_set(mode='OBJECT')

        if modal:
            self.initbm.to_mesh(active.data)

        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        bw = ensure_custom_data_layers(bm)[1]

        mg = build_mesh_graph(bm, debug=debug)
        verts = [v for v in bm.verts if v.select]
        faces = [f for f in bm.faces if f.select]

        if self.init:
            self.init = False

            self.sharps = any(f.smooth for f in faces)

            self.init_panel_decal(active)

        sweeps = get_sweeps_from_fillet(bm, mg, verts, faces, debug=debug)

        if sweeps:
            chamfer_faces = unfuse(bm, faces, sweeps, debug=debug)

            if chamfer_faces:
                chamfer_verts = [v for v in bm.verts if v.select]
                chamfer_mg = build_mesh_graph(bm, debug=debug)

                ret = get_2_rails_from_chamfer(bm, chamfer_mg, chamfer_verts, chamfer_faces, False, debug=debug)

                if ret:
                    chamfer_rails, self.cyclic = ret
                    set_rail_sharps_and_bweights(bm, bw, chamfer_rails, self.cyclic, self.sharps, self.bweights, self.bweight)

                bm.to_mesh(active.data)

                bpy.ops.object.mode_set(mode='EDIT')
                return True

        bpy.ops.object.mode_set(mode='EDIT')
        return False

    def init_panel_decal(self, active):
        if self.decalmachine and active.DM.decaltype == "PANEL":
            self.sharps = False
            self.bweights = False
