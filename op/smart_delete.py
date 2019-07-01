import bpy
from ..utils import itools as itools
from ..utils import mesh as mesh


class SmartDelete(bpy.types.Operator):
    bl_idname = "itools.smart_delete"
    bl_label = "Smart Delete"
    bl_description = "Context Sensitive Deletion"
    bl_options = {'REGISTER', 'UNDO'}

    def smart_delete(cls, context):
        mode = (tuple(bpy.context.scene.tool_settings.mesh_select_mode))

        if mode == 'OBJECT':
            bpy.ops.object.delete()

        elif mode in ['VERT', 'EDGE', 'FACE']:
            bm = get_bmesh()

            if mode == 'VERT':
                bpy.ops.mesh.delete(type='VERT')

            elif mode == 'EDGE':
                selection = itools.get_selected()

                if mesh.is_border(selection):
                    for edge in selection:
                        for face in edge.link_faces:
                            face.select = 1
                    bpy.ops.mesh.delete(type='FACE')

                else:
                    bpy.ops.mesh.dissolve_edges()

            elif mode == 'FACE':
                bpy.ops.mesh.delete(type='FACE')

        elif mode == 'EDIT_CURVE':
            bpy.ops.curve.delete(type='VERT')

        return{'FINISHED'}

    def draw(self, context):
        pass

    def execute(self, context):
        self.smart_delete(context)
        return {'FINISHED'}
