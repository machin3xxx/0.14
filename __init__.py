bl_info = {
    "name": "MESHmachine",
    "author": "MACHIN3",
    "version": (0, 14, 0),
    "blender": (3, 6, 0),
    "location": "Object and Edit Mode Menu: Y key, MACHIN3 N Panel",
    "revision": "br549",
    "description": "The missing essentials.",
    "warning": "",
    "doc_url": "https://machin3.io/MESHmachine/docs",
    "tracker_url": "https://machin3.io/MESHmachine/docs/faq/#get-support",
    "category": "Mesh"}

def reload_modules(name):
    import os
    import importlib

    dbg = False

    from . import registration, items, colors

    for module in [registration, items, colors]:
        importlib.reload(module)

    utils_modules = sorted([name[:-3] for name in os.listdir(os.path.join(__path__[0], "utils")) if name.endswith('.py')])

    for module in utils_modules:
        impline = "from . utils import %s" % (module)

        if dbg:
            print(f"reloading {name}.utils.{module}")

        exec(impline)
        importlib.reload(eval(module))

    from . import handlers
    
    if dbg:
        print("reloading", handlers.__name__)

    importlib.reload(handlers)

    modules = []

    for label in registration.classes:
        entries = registration.classes[label]
        for entry in entries:
            path = entry[0].split('.')
            module = path.pop(-1)

            if (path, module) not in modules:
                modules.append((path, module))

    for path, module in modules:
        if path:
            impline = f"from . {'.'.join(path)} import {module}"
        else:
            impline = f"from . import {module}"

        if dbg:
            print(f"reloading {name}.{'.'.join(path)}.{module}")

        exec(impline)
        importlib.reload(eval(module))

if 'bpy' in locals():
    reload_modules(bl_info['name'])

import bpy
from bpy.props import PointerProperty, IntVectorProperty
from . properties import MeshSceneProperties, MeshObjectProperties
from . handlers import stashes_HUD, stashes_VIEW3D, update_stashes, update_msgbus
from . utils.registration import get_core, get_menus, get_tools, get_prefs, register_classes, unregister_classes, register_keymaps, unregister_keymaps
from . utils.registration import register_plugs, unregister_plugs, register_lockedlib, unregister_lockedlib, register_icons, unregister_icons
from . utils.registration import register_msgbus, unregister_msgbus
from . ui.menus import context_menu

def update_check():
    def hook(resp, *args, **kwargs):
        if resp:
            if resp.text == 'true':
                get_prefs().update_available = True

    import platform
    import hashlib
    from . modules.requests_futures.sessions import FuturesSession

    get_prefs().update_available = False

    machine = hashlib.sha1(platform.node().encode('utf-8')).hexdigest()[0:7]

    headers = {'User-Agent': f"MESHmachine/{'.'.join([str(v) for v in bl_info.get('version')])} Blender/{'.'.join([str(v) for v in bpy.app.version])} ({platform.uname()[0]}; {platform.uname()[2]}; {platform.uname()[4]}; {machine})"}
    session = FuturesSession()

    try:
        session.post("https://drum.machin3.io/update", data={'revision': bl_info['revision']}, headers=headers, hooks={'response': hook})
    except:
        pass

def register():
    global classes, keymaps, icons, owner

    core_classes = register_classes(get_core())

    bpy.types.Scene.MM = PointerProperty(type=MeshSceneProperties)
    bpy.types.Object.MM = PointerProperty(type=MeshObjectProperties)

    bpy.types.WindowManager.plug_mousepos = IntVectorProperty(name="Mouse Position for Plug Insertion", size=2)

    plugs = register_plugs()
    register_lockedlib()

    menu_classlists, menu_keylists = get_menus()
    tool_classlists, tool_keylists = get_tools()

    classes = register_classes(menu_classlists + tool_classlists) + core_classes
    keymaps = register_keymaps(menu_keylists + tool_keylists)

    bpy.types.VIEW3D_MT_object_context_menu.prepend(context_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(context_menu)

    icons = register_icons()

    owner = object()
    register_msgbus(owner)

    bpy.app.handlers.load_post.append(update_msgbus)
    bpy.app.handlers.load_post.append(update_stashes)

    bpy.app.handlers.depsgraph_update_post.append(stashes_HUD)
    bpy.app.handlers.depsgraph_update_post.append(stashes_VIEW3D)

    if get_prefs().registration_debug:
        print(f"Registered {bl_info['name']} {'.'.join([str(i) for i in bl_info['version']])} with {len(plugs)} plug libraries")

        for lib in plugs:
            print(" • plug library: %s" % (lib))

    update_check()

def unregister():
    global classes, keymaps, icons

    debug = get_prefs().registration_debug

    bpy.app.handlers.load_post.remove(update_msgbus)
    bpy.app.handlers.load_post.remove(update_stashes)

    from . handlers import stashesHUD, stashesVIEW3D

    if stashesHUD and "RNA_HANDLE_REMOVED" not in str(stashesHUD):
        bpy.types.SpaceView3D.draw_handler_remove(stashesHUD, 'WINDOW')

    bpy.app.handlers.depsgraph_update_post.remove(stashes_HUD)

    if stashesVIEW3D and "RNA_HANDLE_REMOVED" not in str(stashesVIEW3D):
        bpy.types.SpaceView3D.draw_handler_remove(stashesVIEW3D, 'WINDOW')

    bpy.app.handlers.depsgraph_update_post.remove(stashes_VIEW3D)

    unregister_msgbus(owner)

    unregister_plugs()
    unregister_lockedlib()

    unregister_keymaps(keymaps)

    unregister_icons(icons)

    del bpy.types.Scene.MM
    del bpy.types.Object.MM

    del bpy.types.Scene.userpluglibs
    del bpy.types.WindowManager.newplugidx

    del bpy.types.WindowManager.plug_mousepos

    bpy.types.VIEW3D_MT_object_context_menu.remove(context_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(context_menu)

    unregister_classes(classes)

    if debug:
        print(f"Unregistered {bl_info['name']} {'.'.join([str(i) for i in bl_info['version']])}")
