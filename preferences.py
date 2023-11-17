import bpy
from bpy.props import CollectionProperty, IntProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty
import os
from time import time
from . import bl_info
from . properties import PlugLibsCollection
from . utils.registration import get_path, get_name, get_addon
from . utils.ui import draw_keymap_items, get_keymap_item, get_icon, popup_message
from . utils.draw import draw_split_row
from . utils.library import get_lib
from . items import prefs_tab_items, prefs_plugmode_items

decalmachine = None
machin3tools = None
punchit = None
curvemachine = None
hypercursor = None

thankyou_time = None

class MESHmachinePreferences(bpy.types.AddonPreferences):
    path = get_path()
    bl_idname = get_name()

    registration_debug: BoolProperty(name="Addon Terminal Registration Output", default=True)

    def update_show_looptools_wrappers(self, context):
        if self.show_looptools_wrappers:
            looptools, name, _, _ = get_addon('LoopTools')

            if not looptools:
                bpy.ops.preferences.addon_enable(module=name)

    show_in_object_context_menu: BoolProperty(name="Show in Object Mode Context Menu", default=False)
    show_in_mesh_context_menu: BoolProperty(name="Show in Edit Mode Context Menu", default=False)
    show_looptools_wrappers: BoolProperty(name="Show LoopTools Wrappers", default=False, update=update_show_looptools_wrappers)
    show_mesh_split: BoolProperty(name="Show Mesh Split tool", default=False)
    show_delete: BoolProperty(name="Show Delete Menu", default=False)

    modal_hud_scale: FloatProperty(name="HUD Scale", default=1, min=0.5, max=10)
    modal_hud_color: FloatVectorProperty(name="HUD Font Color", subtype='COLOR', default=[1, 1, 1], size=3, min=0, max=1)
    modal_hud_hints: BoolProperty(name="Show Hints", default=True)
    modal_hud_follow_mouse: BoolProperty(name="Follow Mouse", default=True)
    modal_hud_timeout: FloatProperty(name="Timeout", description="Factor to speed up or slow down time based modal operators like Create Stash, Boolean, Symmetrize drawing, etc", default=1, min=0.5)
    stashes_hud_offset: IntProperty(name="Stashes HUD offset", default=0, min=0)
    symmetrize_flick_distance: IntProperty(name="Flick Distance", default=75, min=20, max=1000)

    show_sidebar_panel: BoolProperty(name="Show Sidebar Panel", default=True)

    def update_matcap(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        matcaps = [mc.name for mc in context.preferences.studio_lights if os.path.basename(os.path.dirname(mc.path)) == "matcap"]

        if self.matcap not in matcaps:
            self.avoid_update = True
            self.matcap = "NOT FOUND"

    matcap: StringProperty(name="Normal Transfer Matcap", default="toon.exr", update=update_matcap)
    experimental: BoolProperty(name="Experimental Features", default=False)

    assetspath: StringProperty(name="Plug Libraries", subtype='DIR_PATH', default=os.path.join(path, "assets", "Plugs"))
    pluglibsCOL: CollectionProperty(type=PlugLibsCollection)
    pluglibsIDX: IntProperty()

    newpluglibraryname: StringProperty(name="New Library Name")

    reverseplugsorting: BoolProperty(name="Reverse Plug Sorting (requires library reload or Blender restart)", default=False)
    libraryscale: IntProperty(name="Size of Plug Libary Icons", default=4, min=1, max=20)
    plugsinlibraryscale: IntProperty(name="Size of Icons in Plug Libaries", default=4, min=1, max=20)
    showplugcount: BoolProperty(name="Show Plug Count next to Library Name", default=True)
    showplugbutton: BoolProperty(name="Show Plug Buttons below Libraries", default=True)
    showplugbuttonname: BoolProperty(name="Show Plug Name on Insert Button", default=False)
    showplugnames: BoolProperty(name="Show Plug Names in Plug Libraries", default=False)
    plugxraypreview: BoolProperty(name="Auto-X-Ray the plug and its subsets, when inserting Plug into scene", default=True)
    plugfadingwire: BoolProperty(name="Fading wire frames (experimental)", default=False)
    plugcreator: StringProperty(name="Plug Creator", default="MACHIN3 - machin3.io, @machin3io")

    def update_tabs(self, context):
        if self.tabs == "ABOUT":
            self.addons_MESHmachine = get_addon('MESHmachine')[0]
            self.addons_MACHIN3tools = get_addon('MACHIN3tools')[0]
            self.addons_GrouPro = get_addon('Group Pro')[0]
            self.addons_BatchOps = get_addon('Batch Operations™')[0]
            self.addons_HardOps = get_addon('Hard Ops 9')[0]
            self.addons_BoxCutter = get_addon('BoxCutter')[0]

    tabs: bpy.props.EnumProperty(name="Tabs", items=prefs_tab_items, default="GENERAL", update=update_tabs)
    def update_plugmode(self, context):
        if self.plugremovemode is True:
            self.plugmode = "REMOVE"
        else:
            self.plugmode = "INSERT"

    plugmode: EnumProperty(name="Plug Mode", items=prefs_plugmode_items, default="INSERT")
    plugremovemode: BoolProperty(name="Remove Plugs", default=False, update=update_plugmode)

    update_available: BoolProperty(name="Update is available", default=False)
    avoid_update: BoolProperty(default=False)
    def draw(self, context):
        layout = self.layout

        self.draw_thank_you(layout)

        column = layout.column(align=True)
        row = column.row()
        row.prop(self, "tabs", expand=True)

        box = column.box()

        if self.tabs == "GENERAL":
            self.draw_general_tab(box)
        elif self.tabs == "PLUGS":
            self.draw_plugs_tab(box)
        elif self.tabs == "ABOUT":
            self.draw_about_tab(box)

    def draw_general_tab(self, box):
        split = box.split()

        b = split.box()

        self.draw_addon(b)

        self.draw_menu(b)

        self.draw_tools(b)

        self.draw_HUD(b)

        self.draw_view3d(b)

        b = split.box()

        self.draw_keymaps(b)

    def draw_plugs_tab(self, box):
        split = box.split()

        b = split.box()
        b.label(text="Plug Libraries")

        self.draw_assets_path(b)

        self.draw_plug_libraries(b)

        b = split.box()
        b.label(text="Plug Settings")

        self.draw_asset_loaders(b)

        self.draw_plug_creation(b)

    def draw_about_tab(self, box):
        split = box.split()

        b = split.box()
        b.label(text="MACHIN3")

        self.draw_machin3(b)

        b = split.box()
        b.label(text="Get More Plugs")
        self.draw_plug_resources(b)

    def draw_addon(self, layout):
        box = layout.box()
        box.label(text="Addon")

        column = box.column()

        draw_split_row(self, column, 'registration_debug', label='Print Addon Registration Output in System Console')

    def draw_menu(self, layout):
        box = layout.box()
        box.label(text="Menu")

        column = box.column(align=True)

        draw_split_row(self, column, 'show_in_mesh_context_menu', label="Show in Blender's Edit Mesh Context Menu")
        draw_split_row(self, column, 'show_in_object_context_menu', label="Show in Blender's Object Context Menu")

        column.separator()

        draw_split_row(self, column, 'show_looptools_wrappers', label="Show LoopTools Wrappers")

        if get_keymap_item('Mesh', 'machin3.call_mesh_machine_menu', 'X') or get_keymap_item('Object Mode', 'machin3.call_mesh_machine_menu', 'X'):
            draw_split_row(self, column, 'show_delete', label="Show Delete Menu")

        if get_keymap_item('Mesh', 'machin3.call_mesh_machine_menu', 'Y'):
            draw_split_row(self, column, 'show_mesh_split', label="Show Mesh Split Tool")

    def draw_tools(self, layout):
        box = layout.box()
        box.label(text="Tools")

        b = box.box()
        b.label(text="Normal Transfer")

        column = b.column()

        draw_split_row(self, column, 'matcap', label="Name of Matcap used for Surface Check.", info="Leave Empty, to disable")

        b = box.box()
        b.label(text="Symmetrize")

        column = b.column()

        draw_split_row(self, column, 'symmetrize_flick_distance', label="Flick Distance")

        b = box.box()
        b.label(text="Experimental")

        column = b.column()

        draw_split_row(self, column, 'experimental', label="Use Experimental Features, at your own risk", warning="Not covered by Product Support!")

    def draw_HUD(self, layout):
        box = layout.box()
        box.label(text="HUD")

        column = box.column(align=True)

        row = draw_split_row(self, column, 'modal_hud_hints', label="Show Hints", factor=0.6)
        draw_split_row(self, row, 'modal_hud_scale', label="HUD Scale", factor=0.6)
        draw_split_row(self, row, 'modal_hud_color', label="Color", expand=False, factor=0.6)

        row = draw_split_row(self, column, 'modal_hud_follow_mouse', label="Follow Muuse", factor=0.6)
        draw_split_row(self, row, 'modal_hud_timeout', label="Timeout", factor=0.6)
        draw_split_row(self, row, 'stashes_hud_offset', label="Stashes Offset", expand=False, factor=0.6)

    def draw_view3d(self, layout):
        box = layout.box()
        box.label(text="View 3D")

        column = box.column()

        draw_split_row(self, column, 'show_sidebar_panel', label="Show Sidebar Panel")

    def draw_keymaps(self, layout):
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user

        from . registration import keys as keysdict

        box = layout.box()
        box.label(text="Keymaps")

        column = box.column()

        for name, keylist in keysdict.items():
            draw_keymap_items(kc, name, keylist, column)

    def draw_assets_path(self, layout):
        box = layout.box()
        column = box.column()

        column.prop(self, "assetspath", text="Location")

    def draw_plug_libraries(self, layout):
        box = layout.box()
        box.label(text="Libraries")

        column = box.column()

        row = column.row()
        row.template_list("MACHIN3_UL_plug_libs", "", self, "pluglibsCOL", self, "pluglibsIDX", rows=max(len(self.pluglibsCOL), 6))

        col = row.column(align=True)
        col.operator("machin3.move_plug_library", text="", icon="TRIA_UP").direction = "UP"
        col.operator("machin3.move_plug_library", text="", icon="TRIA_DOWN").direction = "DOWN"
        col.separator()
        col.operator("machin3.clear_plug_libraries", text="", icon="LOOP_BACK")
        col.operator("machin3.reload_plug_libraries", text="", icon_value=get_icon("refresh"))
        col.separator()
        col.operator("machin3.open_plug_library", text="", icon="FILE_FOLDER")
        col.operator("machin3.rename_plug_library", text="", icon="OUTLINER_DATA_FONT")

        _, _, active = get_lib()
        icon = get_icon("cancel") if active and not active.islocked else get_icon("cancel_grey")
        col.operator("machin3.remove_plug_library", text="", icon_value=icon)

        row = column.row()
        row.prop(self, "newpluglibraryname")
        row.operator("machin3.add_plug_library", text="", icon_value=get_icon("plus"))

    def draw_asset_loaders(self, layout):
        box = layout.box()
        box.label(text="Asset Loaders")

        column = box.column(align=True)

        draw_split_row(self, column, 'plugsinlibraryscale', label="Size of Icons in Plug Libraries")
        draw_split_row(self, column, 'reverseplugsorting', label="Reverse Plug Sorting", info="Requires library reload or Blender restart", factor=0.202)
        draw_split_row(self, column, 'showplugcount', label="Show Plug Count next to Library name")
        draw_split_row(self, column, 'showplugnames', label="Show Plug Names in Plug Libraries")
        draw_split_row(self, column, 'showplugbuttonname', label="Show Plug Name on Insert Buttons")
        draw_split_row(self, column, 'plugxraypreview', label="Show Plugs 'In Front' when bringin them into the scene")

    def draw_plug_creation(self, layout):
        box = layout.box()
        column = box.column()

        row = column.split(factor=0.2)
        row.label(text="Plug Creator")
        row.prop(self, "plugcreator", text="")

        row = column.split(factor=0.3)
        row.label()
        row.label(text="Change this, so Plugs created by you, are tagged with your info!", icon="INFO")

    def draw_machin3(self, layout):
        global decalmachine, machin3tools, punchit, curvemachine, hypercursor

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        if punchit is None:
            punchit = get_addon('PUNCHit')[0]

        if curvemachine is None:
            curvemachine = get_addon('CURVEmachine')[0]

        if hypercursor is None:
            hypercursor = get_addon('HyperCursor')[0]

        installed = get_icon('save')
        missing = get_icon('cancel_grey')

        box = layout.box()
        box.label(text="My other Blender Addons")
        column = box.column(align=True)

        row = column.split(factor=0.3, align=True)
        row.scale_y = 1.2
        row.label(text="DECALmachine", icon_value=installed if decalmachine else missing)
        r = row.split(factor=0.2, align=True)
        r.operator("wm.url_open", text="Web", icon='URL').url = "https://decal.machin3.io"
        rr = r.row(align=True)
        rr.operator("wm.url_open", text="Gumroad", icon='URL').url = "https://gumroad.com/a/164689011/fjXBHu"
        rr.operator("wm.url_open", text="Blender Market", icon='URL').url = "https://www.blendermarket.com/products/DECALmachine?ref=1051"

        row = column.split(factor=0.3, align=True)
        row.scale_y = 1.2
        row.label(text="MACHIN3tools", icon_value=installed if machin3tools else missing)
        r = row.split(factor=0.2, align=True)
        r.operator("wm.url_open", text="Web", icon='URL').url = "https://machin3.io"
        rr = r.row(align=True)
        rr.operator("wm.url_open", text="Gumroad", icon='URL').url = "https://gumroad.com/a/164689011/IjsAf"
        rr.operator("wm.url_open", text="Blender Market", icon='URL').url = "https://www.blendermarket.com/products/MACHIN3tools?ref=1051"

        row = column.split(factor=0.3, align=True)
        row.scale_y = 1.2
        row.label(text="PUNCHit", icon_value=installed if punchit else missing)
        r = row.split(factor=0.2, align=True)
        r.operator("wm.url_open", text="Web", icon='URL').url = "https://punch.machin3.io/"
        rr = r.row(align=True)
        rr.operator("wm.url_open", text="Gumroad", icon='URL').url = "https://gumroad.com/a/164689011/irase"
        rr.operator("wm.url_open", text="Blender Market", icon='URL').url = "https://www.blendermarket.com/products/PUNCHit?ref=1051"

        row = column.split(factor=0.3, align=True)
        row.scale_y = 1.2
        row.label(text="CURVEmachine", icon_value=installed if curvemachine else missing)
        r = row.split(factor=0.2, align=True)
        r.operator("wm.url_open", text="Web", icon='URL').url = "https://curve.machin3.io/"
        rr = r.row(align=True)
        rr.operator("wm.url_open", text="Gumroad", icon='URL').url = "https://gumroad.com/a/164689011/okwtf"
        rr.operator("wm.url_open", text="Blender Market", icon='URL').url = "https://www.blendermarket.com/products/CURVEmachine?ref=1051"

        row = column.split(factor=0.3, align=True)
        row.scale_y = 1.2
        row.label(text="HyperCursor", icon_value=installed if hypercursor else missing)
        row.operator("wm.url_open", text="Youtube Playlist, Pre-Release available on Patreon", icon='URL').url = "https://www.youtube.com/playlist?list=PLcEiZ9GDvSdWs1w4ZrkbMvCT2R4F3O9yD"

        box = layout.box()
        box.label(text="Documentation")

        column = box.column()
        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text="Documention", icon='INFO').url = "https://machin3.io/MESHmachine/docs"
        row.operator("wm.url_open", text="Youtube", icon_value=get_icon('youtube')).url = "https://www.youtube.com/watch?v=i68jOGMEUV8&list=PLcEiZ9GDvSdXR9kd4O6cdQN_6i0LOe5lw"
        row.operator("wm.url_open", text="FAQ", icon='QUESTION').url = "https://machin3.io/MESHmachine/docs/faq"
        row.operator("machin3.get_meshmachine_support", text="Get Support", icon='GREASEPENCIL')

        box = layout.box()
        box.label(text="Discussion")

        column = box.column()
        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text="Blender Artists", icon_value=get_icon('blenderartists')).url = "https://blenderartists.org/t/meshmachine/1102529"

        box = layout.box()
        box.label(text="Follow my work")

        column = box.column()
        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text="MACHINƎ.io", icon='WORLD').url = "https://machin3.io"
        row.operator("wm.url_open", text="Twitter", icon_value=get_icon('twitter')).url = "https://twitter.com/machin3io"
        row.operator("wm.url_open", text="Artstation", icon_value=get_icon('artstation')).url = "https://artstation.com/machin3"
        row.operator("wm.url_open", text="Patreon", icon_value=get_icon('patreon')).url = "https://patreon.com/machin3"

    def draw_plug_resources(self, layout):
        column = layout.column()

        row = column.row()
        row.scale_y = 16
        row.operator("wm.url_open", text="Get More Plugs", icon='URL').url = "https://machin3.io/MESHmachine/docs/plug_resources"

    def draw_thank_you(self, layout):
        global thankyou_time

        message = [f"Thank you for purchasing {bl_info['name']}!",
                   "",
                   "Your support allows me to keep developing this addon and future ones, keeps updates free for everyone, and most importantly enables me to provide for my family.",
                   f"If you haven't purchased {bl_info['name']}, please consider doing so."]

        if thankyou_time is None:
            thankypou_path = os.path.join(get_path(), 'thank_you')

            if not os.path.exists(thankypou_path):
                thankyou_time = time()
                msg = message + ['', str(thankyou_time)]

                with open(thankypou_path, mode='w') as f:
                    f.write('\n'.join(m for m in msg))

            else:
                with open(thankypou_path) as f:
                    lines = [l[:-1] for l in f.readlines()]

                try:
                    thankyou_time = float(lines[-1])
                except:
                    thankyou_time = lines[-1]

        if thankyou_time:
            draw_message = False
            message_lifetime = 5

            if isinstance(thankyou_time, float):
                deltatime = (time() - thankyou_time) / 60
                draw_message = deltatime < message_lifetime

            else:
                draw_message = True
                deltatime = 'X'

            if draw_message:

                b = layout.box()
                b.label(text="Thank You!", icon='INFO')

                col = b.column()

                for i in range(2):
                    col.separator()

                for line in message:
                    if line:
                        col.label(text=line)
                    else:
                        col.separator()

                for i in range(3):
                    col.separator()

                col.label(text=f"This message will self-destruct in {message_lifetime - deltatime:.1f} minutes.", icon='SORTTIME')

                for i in range(3):
                    col.separator()

                col.label(text=f"If you have purchased {bl_info['name']} and find this nag-screen annoying, I appologize.")
                col.label(text=f"If you have haven't purchased {bl_info['name']} and find this nag-screen annoying, go fuck yourself.")
