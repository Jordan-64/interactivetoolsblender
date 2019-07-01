import bpy
import bmesh
import itertools
import mesh_f2
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty
from functools import reduce
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_vector_3d, region_2d_to_origin_3d
from mathutils import Vector
import math
 
#Global Variables
ITERATION_LIMIT = 200

#Utility Functions
 
def list_intersection(a, b):
	return list(set(a) & set(b))
 
def list_difference(a,b):
	return list(set(a) - set(b))
 
def get_bmesh():
	return bmesh.from_edit_mesh(bpy.context.edit_object.data)

def get_bmesh_from_obj():
	return bmesh.from_object(bpy.context.active_object.data)

def update_indexes(verts=False, edges=False, faces=False):
	bm = get_bmesh()
	if verts:
		bm.verts.index_update()
	if edges:
		bm.edges.index_update()
	if faces:
		bm.faces.index_update()
	bm.verts.ensure_lookup_table()
	bm.edges.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	bmesh.update_edit_mesh(bpy.context.edit_object.data)
 
def get_selected(verts=False, edges = False, faces = False, get_item = False):
	bm = get_bmesh()
	if verts:
		update_indexes(verts=True)
		selected_verts = []
		for vert in bm.verts:
			if vert.select :
				if get_item:
					selected_verts.append(vert)
				else:
					selected_verts.append(vert.index)
		return selected_verts
	if edges:
		update_indexes(edges=True)
		selected_edges = []
		for edge in bm.edges:
			if edge.select:
				if get_item:
					selected_edges.append(edge)
				else:
					selected_edges.append(edge.index)
		return selected_edges
	if faces:
		update_indexes(faces=True)
		selected_faces = []
		for face in bm.faces:
			if face.select:
				if get_item:
					selected_faces.append(face)
				else:
					selected_faces.append(face.index)
		return selected_faces

def select_from_index(indexes, verts = False,edges = False, faces = False, replace = False, add_to_history = False, deselect = False):
	selection_value = True
	bm = get_bmesh()
	if replace:
		bpy.ops.mesh.select_all(action='DESELECT')
	if deselect:
		selection_value = False
	if verts:
		for index in indexes:
			bm.verts[index].select = selection_value
			if add_to_history:
				bm.select_history.add(bm.verts[index])
	if edges:
		for index in indexes:
			bm.edges[index].select = selection_value
			if add_to_history:
				bm.select_history.add(bm.edges[index])
	if faces:
		for index in indexes:
			bm.faces[index].select = selection_value
			if add_to_history:
				bm.select_history.add(bm.faces[index]) 

def select_from_item(items, verts = False,edges = False, faces = False, replace = False, add_to_history = False, deselect = False):
	selection_value = True
	bm = get_bmesh()
	if replace:
		bpy.ops.mesh.select_all(action='DESELECT')
	if deselect:
		selection_value = False
	if verts:
		for item in items:
			bm.verts[item.index].select = selection_value
			if add_to_history:
				bm.select_history.add(bm.verts[item.index])
	if edges:
		for item in items:
			bm.edges[item.index].select = selection_value
			if add_to_history:
				bm.select_history.add(bm.edges[item.index])
	if faces:
		for item in items:
			bm.faces[item.index].select = selection_value
			if add_to_history:
				bm.select_history.add(bm.faces[item.index])

def verts_share_edge(verts):
	if len(verts) == 2:
		return len(list_intersection(verts[0].link_edges, verts[1].link_edges)) == 1	
	else:
		return False  

def verts_share_face(verts):
	face_list = []
	for vert in verts:
		face_list.append(vert.link_faces)
	face_list = reduce(lambda x,y:list_intersection(x,y) ,face_list)
	if len(face_list) > 0:
		return True
	else:
		return False

#aproximation, might not work all the times
def is_corner_vert(vert):
	cornerVerts = [face for face in vert.link_faces]
	return len(cornerVerts) > 2  
	
def is_border_vert(vert):
	borderEdges = [edge for edge in vert.link_edges if len(edge.link_faces) == 1]
	return len(borderEdges) > 1

def are_border_verts(verts):
	return all(is_border_vert(vert) for vert in verts) 

def is_border_edge(edge):
	return all(is_border_vert(vert) for vert in edge.verts)

#selection needs to be edges
def is_border(selection):
	#every edge must be adjacent with two other edges, if its a closed border the number of adjacent edges should be at least 2 X number edges
	number_adjacent_edges = len([neightbour for edge in selection for verts in edge.verts for neightbour in verts.link_edges if neightbour in selection and neightbour is not edge])
	return all(is_border_edge(edge) for edge in selection) and number_adjacent_edges >= len(selection) * 2 
  
def is_adjacent(selection):
	vert_list = [edge.verts for edge in selection]
	common_vert = reduce(lambda x,y: list_intersection(x, y) , vert_list)
	return len(common_vert) == 1

def is_ring(selection):
	"""
	#Aproximation that should work 98% for now
	#Gets false positives when corners are selected like this: I_ or _I
	"""
	neightbour_Numbers = [edge for edge in selection if len([face for face in edge.link_faces if any(edge2 for edge2 in face.edges if edge2 in selection and edge2 != edge)]) > 0]
	return len(neightbour_Numbers) == len(selection)	

def split_edge_select_vert(change_selection = False):
	selection = get_selected(verts = True)
	bpy.ops.mesh.subdivide()
	if change_selection:
		new_selection = get_selected(verts = True)
		new_selection = list_difference(new_selection, selection)
		select_from_index(new_selection, verts = True,replace = True)
		bpy.context.scene.tool_settings.mesh_select_mode = [True,False,False]
	return new_selection
	 
def quad_fill():
	selection = get_selected(edges = True)
	bpy.ops.mesh.delete(type='FACE')
	select_from_index(selection, edges = True,replace = True)
	bpy.ops.mesh.fill_grid()

#make it smarter
def find_f2_verts(vert):
	vert_list = [edge.other_vert(vert[0]) for edge in vert[0].link_edges if is_border_vert(edge.other_vert(vert[0]))] + vert
	vert_list = list(filter(lambda x: is_border_vert(x) and is_corner_vert(x), vert_list))
	"""
	if vert_list == []:
		border_edges = list(filter(lambda x:is_border_edge(x),[edge for edge in vert_list[0].link_edges]))
		
		bpy.ops.mesh.loop_multi_select(ring=False)
		
		Assuming the verts it gets are border verts
		#1)get all verts in the loop
		#2)get all border and corner verts
		#3)for each filtered vert check if its a neightbour of any other vert that was filtered
		#4)select those instead
		
		return []
	else:
	"""
	return vert_list

#Main Functions

class SetCylindricalObjSides(bpy.types.Operator):
	bl_idname = "mesh.set_cylindrical_sides"
	bl_label = "Set Cylindrical Object Sides"
	bl_description = "Select the ammount of sides for cylindrical object"
	bl_options = {'REGISTER', 'UNDO'}

	def set_cylindrical_obj_sides(self):
		selection = bpy.context.active_object
		print(selection)
		if bpy.context.object.modifiers.find("Cylindrical Sides") > -1:
			bpy.ops.wm.context_modal_mouse('INVOKE_DEFAULT',data_path_iter='selected_editable_objects', data_path_item='modifiers["Cylindrical Sides"].steps', input_scale=0.10000000149011612, header_text='Number of Sides %.f')
		elif bpy.context.mode == 'EDIT_MESH':
			bpy.ops.mesh.separate(type='SELECTED')
			new_selection = bpy.context.selected_objects
			mesh_to_select = list(filter(lambda x:x.name != selection.name, new_selection))
			bpy.ops.object.editmode_toggle()
			bpy.ops.object.select_all(action='DESELECT')
			bpy.data.objects[mesh_to_select[0].name].select_set(state=True)
			bpy.context.view_layer.objects.active = mesh_to_select[0]
			bpy.ops.object.modifier_add(type='SCREW')
			bpy.context.object.modifiers["Screw"].name = "Cylindrical Sides"
			bpy.context.object.modifiers["Cylindrical Sides"].use_merge_vertices = True
			bpy.context.object.modifiers["Cylindrical Sides"].use_normal_calculate = True
			bpy.ops.wm.context_modal_mouse('INVOKE_DEFAULT',data_path_iter='selected_editable_objects', data_path_item='modifiers["Cylindrical Sides"].steps', input_scale=0.10000000149011612, header_text='Number of Sides %.f')

	def execute(self,context):
		self.set_cylindrical_obj_sides()
		return {'FINISHED'}

class SmartFlow (bpy.types.Operator):
	bl_idname = "mesh.smart_flow"
	bl_label = "Smart Flow"
	bl_description = "Smart Edge Flow"
	bl_options = {'REGISTER', 'UNDO'}

	def smart_hard_ops(self):
		selectionMode = (tuple(bpy.context.scene.tool_settings.mesh_select_mode))
		#if Vertex is selected
		if selectionMode[0]:
			print("if a loop is selected then distance fix, else Relax")
		#if Edge is selected
		elif selectionMode[1]:
			print("If border is selected then draw crcle, If Loop is selected then do loop set flow. If ring is selected then do if")
		elif selectionMode[2]:
		#if Face is selected then flatten		   
			bpy.ops.mesh.inset('INVOKE_DEFAULT')

	def execute(self, context):
		self.smart_hard_ops()
		return{'FINISHED'}





class QuickPivot(bpy.types.Operator):
	bl_idname = "mesh.quick_pivot"
	bl_label = "Quick Pivot Setup"
	bl_description = "Quick Pivot Setup based on selection"
	bl_options = {'REGISTER', 'UNDO'}
	def quick_pivot(self,context):
		if context.mode == 'OBJECT':
			bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
		elif context.mode == 'EDIT_MESH':
			cl = context.scene.cursor.location
			pos2 = (cl[0],cl[1],cl[2])
			bpy.ops.view3d.snap_cursor_to_selected()
			bpy.ops.object.editmode_toggle()
			bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
			bpy.ops.object.editmode_toggle()
			context.scene.cursor.location = (pos2[0],pos2[1],pos2[2])
	
	def execute(self, context):
		self.quick_pivot(context)
		return{'FINISHED'}

class SimpleEditPivot(bpy.types.Operator):
	bl_idname = "mesh.simple_edit_pivot"
	bl_label = "Simple Edit Pivot"
	bl_description = "Edit pivot position and scale"
	bl_options = {'REGISTER', 'UNDO'}

	def create_pivot(self, context, obj):
		bpy.ops.object.empty_add(type='ARROWS', location= obj.location)
		pivot = bpy.context.active_object
		pivot.name = obj.name + ".PivotHelper"
		pivot.location = obj.location
		print("Pivot")

	def get_pivot(self,context, obj):
		pivot = obj.name + ".PivotHelper"
		if bpy.data.objects.get(pivot) is None:
			return False
		else:
			bpy.data.objects[obj.name].select_set(False)
			bpy.data.objects[pivot].select_set(True)
			context.view_layer.objects.active = bpy.data.objects[pivot]
			return True

	def apply_pivot(self,context, pivot):
		obj = bpy.data.objects[pivot.name[:-12]]
		piv_loc = pivot.location
		#I need to create piv as it seem like the pivot location is passed by reference? Still no idea why this happens
		cl = context.scene.cursor.location
		piv = (cl[0],cl[1],cl[2])
		context.scene.cursor.location = piv_loc
		bpy.context.view_layer.objects.active = obj
		bpy.data.objects[obj.name].select_set(True)
		bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
		context.scene.cursor.location = (piv[0],piv[1],piv[2])
		#Select pivot, delete it and select obj again
		bpy.data.objects[obj.name].select_set(False)
		bpy.data.objects[pivot.name].select_set(True)
		bpy.ops.object.delete()
		bpy.data.objects[obj.name].select_set(True)
		context.view_layer.objects.active = obj

	def execute(self, context):
		obj = bpy.context.active_object
		if  obj.name.endswith(".PivotHelper"):
			self.apply_pivot(context, obj)
		elif self.get_pivot(context, obj):
			piv = bpy.context.active_object
		else:
			self.create_pivot(context,obj)
		return{'FINISHED'}





class QuickAlign(bpy.types.Operator):
	bl_idname = "mesh.quick_align"
	bl_label = "Quick Align"
	bl_description = "Quickly Align Objects"
	bl_options = {'REGISTER', 'UNDO'}
	
	def mouse_raycast(self, context, event):

		region = context.region
		rv3d = context.region_data
		coord = event.mouse_region_x, event.mouse_region_y
		# get the ray from the viewport and mouse
		view_vector = region_2d_to_vector_3d(region, rv3d, coord)
		ray_origin = region_2d_to_origin_3d(region, rv3d, coord,clamp = 20)
		ray_target = None
		ray_target = ray_origin + (view_vector * 1000)
		ray_target.normalized()

		result, location, normal, index, object, matrix = context.scene.ray_cast(context.view_layer, ray_origin,ray_target)
		if bpy.context.mode == 'OBJECT':
			if result and not object.select_get():
				bpy.ops.view3d.select('INVOKE_DEFAULT', extend=True, deselect=False, enumerate=False, toggle=False)
		else:
			bpy.ops.view3d.select('INVOKE_DEFAULT', extend=True, deselect=False, enumerate=False, toggle=False)

	def invoke(self, context, event):
		selected = bpy.context.active_object
		if len(bpy.context.selected_objects) == 1:
			self.mouse_raycast(context, event)
			if len(bpy.context.selected_objects) > 1:
				newactive = bpy.context.active_object
				bpy.ops.object.align(align_mode='OPT_2', align_axis={'X', 'Y', 'Z'})
				bpy.data.objects[newactive.name].select_set(False)
				bpy.context.view_layer.objects.active = selected
			else:
				print("No second object selected")
		elif len(bpy.context.selected_objects) > 1:
			bpy.ops.object.align(align_mode='OPT_2', align_axis={'X', 'Y', 'Z'})

		return {'FINISHED'}

	def execute(self, context):
		print("Selection test")
		return {'FINISHED'}

class QuickRadialSymmetry(bpy.types.Operator):
	bl_idname = "mesh.radial_symmetry"
	bl_label = "Quick Radial Symmetry"
	bl_description = "Setup a Quick Radial Symmetry"
	bl_options = {'REGISTER', 'UNDO'}

	mouseX = 0.0
	initial_pos_x = 0.0
	sym_count = 0.0
	sym_axis = 0
	initial_sym_axis = 0
	initial_sym_count = 0
	offset_obj = "Empty"
	selection = "Empty"
	senitivity = 0.01
	modkey = 0

	def setup_symmetry(self, context, selection):
		if selection is not []:
			sel_pivot = selection.location
			bpy.ops.object.empty_add(type='ARROWS', location=sel_pivot)
			symmetry_center = bpy.context.active_object
			#symmetry_center.hide_viewport = True
			symmetry_center.rotation_euler = (0, 0, math.radians(120))
			symmetry_center.name = selection.name + ".SymmetryPivot"
			print(symmetry_center.name)
			bpy.context.view_layer.objects.active = selection
			bpy.ops.object.modifier_add(type='ARRAY')
			selection.modifiers["Array"].name = "Radial Symmetry"
			selection.modifiers["Radial Symmetry"].relative_offset_displace[0] = 0
			selection.modifiers["Radial Symmetry"].count = 3
			selection.modifiers["Radial Symmetry"].offset_object = bpy.data.objects[symmetry_center.name]
			selection.modifiers["Radial Symmetry"].use_object_offset = True
		else:
			print("Select 1 object to create radial symmetry")

	def calculate_iterations(self,context, event, selection):
		self.mouse_x = event.mouse_x
		self.sym_count = self.initial_sym_count + int(((self.mouse_x - self.initial_pos_x) * self.senitivity))
		if self.sym_count < 1:
			self.sym_count = 1
			self.initial_pos_x = self.mouse_x
		self.selection.modifiers["Radial Symmetry"].count = self.sym_count
	
	def calculate_axis(self,context, event, selection):
		self.mouse_x = event.mouse_x
		self.sym_axis = int((self.initial_sym_axis  + (self.mouse_x - self.initial_pos_x) * self.senitivity ) % 3)
	
	def calculate_rotation(self, axis, selection):
		if axis == 0:
			self.offset_obj.rotation_euler = (math.radians(360/ self.sym_count), 0, 0)	
		elif axis == 1:
			self.offset_obj.rotation_euler = (0 , math.radians(360/ self.sym_count), 0)
		elif axis == 2:
			self.offset_obj.rotation_euler = (0,0,math.radians(360/ self.sym_count))

	def recover_settings(self,context, selection):
		self.initial_sym_count = selection.modifiers["Radial Symmetry"].count 
		self.offset_obj = selection.modifiers["Radial Symmetry"].offset_object
		rotation = selection.modifiers["Radial Symmetry"].offset_object.rotation_euler
		if rotation[0] > 0:
			self.initial_sym_axis = 0
		elif rotation[1] > 0:
			self.initial_sym_axis = 1
		elif rotation[2] > 0:
			self.initial_sym_axis = 2
		self.sym_axis = self.initial_sym_axis
		self.sym_count = self.initial_sym_count

	def __init__(self):
		print("Start")

	def __del__(self):
		print("End")

	def execute(self, context):
		return{'FINISHED'}

	def modal(self, context, event):
		if event.type == 'MOUSEMOVE':  # Apply
			if event.ctrl:
				if self.modkey is not 1:
					self.modkey = 1
					self.initial_pos_x = event.mouse_x
					self.initial_sym_count = self.sym_count 
				self.calculate_axis(context, event, self.selection)
			else:
				if self.modkey is not 0:
					self.modkey = 0
					self.initial_pos_x = event.mouse_x
					self.initial_sym_axis = self.sym_axis
				self.calculate_iterations(context, event, self.selection)
			self.calculate_rotation(self.sym_axis, self.selection)

            	
		elif event.type == 'LEFTMOUSE':  # Confirm
			if event.value == 'RELEASE':
 				return {'FINISHED'}
		elif event.type in {'RIGHTMOUSE', 'ESC'}:  # Confirm
			return {'CANCELLED'}
		return {'RUNNING_MODAL'}
	
	def invoke(self, context, event):
		self.initial_pos_x = event.mouse_x
		self.selection = bpy.context.active_object
		if self.selection.modifiers.find("Radial Symmetry") < 0:
			self.setup_symmetry(context, self.selection)
		self.recover_settings(context, self.selection)
		self.execute(context)
		context.window_manager.modal_handler_add(self)
		return {'RUNNING_MODAL'}

class SmartExtrude(bpy.types.Operator):
	bl_idname = "mesh.smart_extrude_modal"
	bl_label = "Smart Extrude Modal"
	bl_description = "Context Sensitive Extrude operation"
	bl_options = {'REGISTER', 'UNDO'}

	initial_mouse_pos = Vector((0,0,0))
	translation_accumulator = Vector((0,0,0))
	initial_pos = Vector((0,0,0))
	sensitivity = 1

	def mouse_2d_to_3d(self,context, event):
		x, y = event.mouse_region_x, event.mouse_region_y
		location = region_2d_to_location_3d(context.region, context.space_data.region_3d, (x, y), (0, 0, 0))
		return Vector(location)

	#Not Needed, delete later
	def get_verts_center(self):
		bm = get_bmesh()
		obj = bpy.context.active_object
		selectionMode = (tuple(bpy.context.scene.tool_settings.mesh_select_mode))
		if selectionMode[0]:
			verts = get_selected(verts=True, get_item = True)
		elif selectionMode[1]:
			edges = get_selected(edges=True, get_item = True)
			verts = [edge.verts for edge in edges]
			verts = [vert for vert_pair in verts for vert in vert_pair]
			verts = list(set(verts))
		elif selectionMode[2]:
			faces = get_selected(faces=True, get_item = True)
			verts = [face.verts for face in faces]
			verts = [vert for vert_pair in verts for vert in vert_pair]
			verts = list(set(verts))
		verts_center = reduce(lambda x, y: x + y, [obj.matrix_world @ vert.co for vert in verts]) 
		#verts_center = reduce(lambda x, y: x + y, [vert.co for vert in verts]) 
		verts_center /= len(verts)
		return verts_center

	def calculate_translation(self,context,event):
		translation = Vector((0,0,0))
		for area in context.screen.areas:
			if area.type == "VIEW_3D":
				new_mouse_pos = self.mouse_2d_to_3d(context, event)
			else:
				new_mouse_pos = self.initial_mouse_pos
		increment = (new_mouse_pos - self.initial_mouse_pos) * self.sensitivity
		increment_abs = [abs(value) for value in increment]
		axis = list(increment_abs).index(max(increment_abs))
		if axis == 0:
			translation[0] = increment[0] - self.translation_accumulator[0]
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = -self.translation_accumulator[2] 
		elif axis == 1:
			translation[0] = -self.translation_accumulator[0]  
			translation[1] = increment[1] - self.translation_accumulator[1]
			translation[2] = -self.translation_accumulator[2] 
		elif axis == 2:
			translation[0] = -self.translation_accumulator[0] 
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = increment[2] - self.translation_accumulator[2]

		#Debug
		"""
		print("INITIAL VERT POS : %s" % (self.initial_pos))
		print("INITIAL MOUSE POS : %s " % (self.initial_mouse_pos))
		print("NEW MOUSE POS : %s " % (new_mouse_pos))
		print("INCREMENT : %s " % (increment))
		print("ACCUMULATOR : %s " % (self.translation_accumulator))
		print("TRANSLATION: %s " % (translation))
		"""
		self.translation_accumulator += translation 
		bpy.ops.transform.translate(value = translation, orient_type = 'GLOBAL')
		return True

	def calculate_rotation(self,context,event):
		translation = Vector((0,0,0))
		for area in context.screen.areas:
			if area.type == "VIEW_3D":
				new_mouse_pos = self.mouse_2d_to_3d(context, event)
			else:
				new_mouse_pos = self.initial_mouse_pos
		increment = (new_mouse_pos - self.initial_mouse_pos) * self.sensitivity * 0.1
		increment_abs = [abs(value) for value in increment]
		axis = list(increment_abs).index(max(increment_abs))
		if axis == 0:
			translation[0] = increment[0] - self.translation_accumulator[0]
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = -self.translation_accumulator[2] 
			rot_axis = 'X'
			translation_axis = increment[0] - self.translation_accumulator[0]
		elif axis == 1:
			translation[0] = -self.translation_accumulator[0]  
			translation[1] = increment[1] - self.translation_accumulator[1]
			translation[2] = -self.translation_accumulator[2] 
			rot_axis = 'Y'
			translation_axis = increment[1] - self.translation_accumulator[1]
		elif axis == 2:
			translation[0] = -self.translation_accumulator[0] 
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = increment[2] - self.translation_accumulator[2]
			rot_axis = 'Z'
			translation_axis = increment[2] - self.translation_accumulator[2]
		self.translation_accumulator += translation 
		bpy.ops.transform.rotate(value = translation_axis, axis =  rot_axis,orient_type = 'GLOBAL')
		return True

	def context_sensitive_extend(self,context):
		if context.mode == 'OBJECT':
			if len(context.selected_objects) > 0:
				initial_pos = context.selected_objects[0].location
				bpy.ops.object.duplicate()
			else:
				return {'FINISHED'}
		
		elif context.mode == 'EDIT_MESH':
			bm = get_bmesh()
			selectionMode = (tuple(context.scene.tool_settings.mesh_select_mode))
			if selectionMode[1]:
				selection = get_selected(edges = True, get_item = True)
				if all(is_border_edge(edge) for edge in selection):
					bpy.ops.mesh.extrude_edges_move(MESH_OT_extrude_edges_indiv=None, TRANSFORM_OT_translate=None)
				else:
					return {'FINISHED'}
			else:
				bpy.ops.mesh.duplicate(mode=1)
		elif context.mode == 'EDIT_CURVE':
			bpy.ops.curve.extrude_move(CURVE_OT_extrude={"mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, False), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
			print("Curve")
			#self.initial_pos = self.get_verts_center()

	def __init__(self):
		self.initial_mouse_pos = Vector((0,0,0))
		self.translation_accumulator = Vector((0,0,0))
		self.initial_pos = Vector((0,0,0))
		print("Start")

	def __del__(self):
		print("End")

	def execute(self, context):
		return {'FINISHED'}

	def modal(self, context, event):
		if event.type == 'MOUSEMOVE':  # Apply
			self.calculate_translation(context,event)
			self.execute(context)
		elif event.type == 'LEFTMOUSE':  # Confirm
			if event.value == 'RELEASE':
 				return {'FINISHED'}
		elif event.type in {'RIGHTMOUSE', 'ESC'}:  # Confirm
			bpy.ops.transform.translate(value = (Vector((0,0,0)) - self.translation_accumulator), orient_type = 'GLOBAL')
			SmartDelete.smart_delete(context)
			return {'CANCELLED'}
		return {'RUNNING_MODAL'}
			
	def invoke(self, context, event):
		self.initial_mouse_pos = self.mouse_2d_to_3d(context, event)
		self.context_sensitive_extend(context)
		self.execute(context)
		context.window_manager.modal_handler_add(self)
		return {'RUNNING_MODAL'}

class SmartTranslate(bpy.types.Operator):
	bl_idname = "mesh.smart_translate_modal"
	bl_label = "Smart Translate"
	bl_description = "Smart Translate Tool"
	bl_options = {'REGISTER', 'UNDO'}

	initial_mouse_pos = Vector((0,0,0))
	translation_accumulator = Vector((0,0,0))
	initial_pos = Vector((0,0,0))
	sensitivity = 1

	def mouse_2d_to_3d(self,context, event):
		x, y = event.mouse_region_x, event.mouse_region_y
		location = region_2d_to_location_3d(context.region, context.space_data.region_3d, (x, y), (0, 0, 0))
		return Vector(location)

	def calculate_translation(self,context,event):
		translation = Vector((0,0,0))
		for area in context.screen.areas:
			if area.type == "VIEW_3D":
				new_mouse_pos = self.mouse_2d_to_3d(context, event)
			else:
				new_mouse_pos = self.initial_mouse_pos
		increment = (new_mouse_pos - self.initial_mouse_pos) * self.sensitivity
		increment_abs = [abs(value) for value in increment]
		axis = list(increment_abs).index(max(increment_abs))
		if axis == 0:
			translation[0] = increment[0] - self.translation_accumulator[0]
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = -self.translation_accumulator[2] 
		elif axis == 1:
			translation[0] = -self.translation_accumulator[0]  
			translation[1] = increment[1] - self.translation_accumulator[1]
			translation[2] = -self.translation_accumulator[2] 
		elif axis == 2:
			translation[0] = -self.translation_accumulator[0] 
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = increment[2] - self.translation_accumulator[2]
		self.translation_accumulator += translation 
		bpy.ops.transform.translate(value = translation, orient_type = 'GLOBAL')
		return True

	def calculate_rotation(self,context,event):
		translation = Vector((0,0,0))
		for area in context.screen.areas:
			if area.type == "VIEW_3D":
				new_mouse_pos = self.mouse_2d_to_3d(context, event)
			else:
				new_mouse_pos = self.initial_mouse_pos
		increment = (new_mouse_pos - self.initial_mouse_pos) * self.sensitivity * 0.1
		increment_abs = [abs(value) for value in increment]
		axis = list(increment_abs).index(max(increment_abs))
		if axis == 0:
			translation[0] = increment[0] - self.translation_accumulator[0]
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = -self.translation_accumulator[2] 
			rot_axis = 'Y'
			translation_axis = increment[0] - self.translation_accumulator[0]
		elif axis == 1:
			translation[0] = -self.translation_accumulator[0]  
			translation[1] = increment[1] - self.translation_accumulator[1]
			translation[2] = -self.translation_accumulator[2] 
			rot_axis = 'Z'
			translation_axis = increment[1] - self.translation_accumulator[1]
		elif axis == 2:
			translation[0] = -self.translation_accumulator[0] 
			translation[1] = -self.translation_accumulator[1] 
			translation[2] = increment[2] - self.translation_accumulator[2]
			rot_axis = 'X'
			translation_axis = increment[2] - self.translation_accumulator[2]
		self.translation_accumulator += translation
		bpy.ops.transform.rotate(value = translation[0], orient_axis =  'X',orient_type = 'GLOBAL')
		bpy.ops.transform.rotate(value = translation[1], orient_axis =  'Z',orient_type = 'GLOBAL') 
		bpy.ops.transform.rotate(value = translation[2], orient_axis =  'Y',orient_type = 'GLOBAL')
		return True

	def __init__(self):
		self.initial_mouse_pos = Vector((0,0,0))
		self.translation_accumulator = Vector((0,0,0))
		self.initial_pos = Vector((0,0,0))
		print("Start")

	def __del__(self):
		print("End")

	def execute(self, context):
		return {'FINISHED'}

	def modal(self, context, event):
		if event.type == 'MOUSEMOVE':  # Apply
			self.calculate_translation(context,event)
			self.execute(context)
		elif event.type == 'MIDDLEMOUSE':  # Confirm
			if event.value == 'RELEASE':
 				return {'FINISHED'}
		elif event.type in {'RIGHTMOUSE', 'ESC'}:  # Confirm
			bpy.ops.transform.translate(value = - self.translation_accumulator, orient_type = 'GLOBAL')
			return {'CANCELLED'}
		return {'RUNNING_MODAL'}
			
	def invoke(self, context, event):
		self.initial_mouse_pos = self.mouse_2d_to_3d(context, event)
		self.execute(context)
		context.window_manager.modal_handler_add(self)
		return {'RUNNING_MODAL'}

class QuickFFD(bpy.types.Operator):
	bl_idname = "mesh.quick_ffd"
	bl_label = "Quick FFD"
	bl_description = "Setup a Quick FFD"
	bl_options = {'REGISTER', 'UNDO'}

	mouseX = 0.0
	initial_pos_x = 0.0
	sym_count = 0.0
	sym_axis = 0
	initial_sym_axis = 0
	initial_sym_count = 0
	offset_obj = "Empty"
	selection = "Empty"
	senitivity = 0.01
	modkey = 0

	def setup_ffd(self, context, selection):
		if selection is not []:
			if context.mode == 'OBJECT':
				verts = selection.data.vertices
				vert_positions = [vert.co @ selection.matrix_world for vert in verts] 
				rotation = bpy.data.objects[selection.name].rotation_euler
			elif context.mode == 'EDIT_MESH':
				bmesh = get_bmesh()
				minimum = Vector()
				maximum = Vector()
				selectionMode = (tuple(bpy.context.scene.tool_settings.mesh_select_mode))
				if selectionMode[0]:
					verts = get_selected(verts=True, get_item = True)
				elif selectionMode[1]:
					edges = get_selected(edges=True, get_item = True)
					verts = [edge.verts for edge in edges]
					verts = [vert for vert_pair in verts for vert in vert_pair]
					verts = list(set(verts))
				elif selectionMode[2]:
					faces = get_selected(faces=True, get_item = True)
					verts = [face.verts for face in faces]
					verts = [vert for vert_pair in verts for vert in vert_pair]
					verts = list(set(verts))
				vert_positions = [(selection.matrix_world @ vert.co) for vert in verts]
				#Make vertex group
				selection.vertex_groups.new(name = "ffd_group")
				bpy.ops.object.vertex_group_assign()
				rotation = Vector()
				bpy.ops.object.editmode_toggle()
			#calculate positions
			minimum = Vector()
			maximum = Vector()
			for axis in range(3):
				poslist = [pos[axis] for pos in vert_positions]
				maximum[axis] = max(poslist)
				minimum[axis] = min(poslist)
			location = (maximum + minimum) / 2 
			dimensions = maximum - minimum
			#add lattice			
			bpy.ops.object.add(type='LATTICE', enter_editmode=False, location=(0, 0, 0))
			ffd = bpy.context.active_object
			ffd.data.use_outside = True
			ffd.name = selection.name + ".Lattice"
			ffd.data.interpolation_type_u = 'KEY_LINEAR'
			ffd.data.interpolation_type_v = 'KEY_LINEAR'
			ffd.data.interpolation_type_w = 'KEY_LINEAR'
			ffd.location = location
			ffd.scale = dimensions
			ffd.rotation_euler = rotation
			bpy.context.view_layer.objects.active = selection
			bpy.ops.object.modifier_add(type='LATTICE')
			selection.modifiers["Lattice"].object = ffd
			selection.modifiers["Lattice"].vertex_group = "ffd_group"
			bpy.context.view_layer.objects.active = ffd
			#Deselect obj, select FFD and make it active, switch to edit mode
			bpy.data.objects[selection.name].select_set(False)
			bpy.data.objects[ffd.name].select_set(True)
			bpy.ops.object.editmode_toggle()

	def apply_ffd(self, context, ffd):
		if context.mode == 'EDIT_MESH':
			bpy.ops.object.editmode_toggle()
		obj = bpy.data.objects[ffd.name[:-8]]
		bpy.data.objects[ffd.name].select_set(False)
		bpy.data.objects[obj.name].select_set(True)
		bpy.context.view_layer.objects.active = obj
		bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Lattice")
		#Delete vertex group
		vg = obj.vertex_groups.get("ffd_group")
		if vg is not None:
			obj.vertex_groups.remove(vg)
		#Delete lattice
		bpy.data.objects[obj.name].select_set(False)
		bpy.data.objects[ffd.name].select_set(True)
		bpy.ops.object.delete()
		bpy.data.objects[obj.name].select_set(True)
		bpy.ops.object.editmode_toggle()

	def get_ffd(self,context, obj):
		ffd = obj.name + ".Lattice"
		if bpy.data.objects.get(ffd) is None:
			return False
		else:
			bpy.data.objects[obj.name].select_set(False)
			bpy.data.objects[ffd].select_set(True)
			context.view_layer.objects.active = bpy.data.objects[ffd]
			bpy.ops.object.editmode_toggle()
			return True

	def execute(self, context):
		selection = bpy.context.active_object
		if selection.name.endswith(".Lattice"):
			self.apply_ffd(context, selection)
		elif self.get_ffd(context, selection):
			ffd = bpy.context.active_object
		else:
			self.setup_ffd(context, selection)
		return{'FINISHED'}
	
####### UV SCRIPTS #########

def selected_uv_verts_pos():
	bm = get_bmesh()
	uv_layer = bm.loops.layers.uv.verify()
	verts_loc = [loop[uv_layer].uv for face in bm.faces for loop in face.loops if loop[uv_layer].select]
	return verts_loc

class QuickRotateUv90Pos(bpy.types.Operator):
	bl_idname = "uv.rotate_90_pos"
	bl_label = "Rotate UV 90 Pos"
	bl_description = "Rotate Uvs +90 degrees"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		original_pos = selected_uv_verts_pos()
		print(original_pos)
		#original_pos = reduce((lambda x, y: x + y), original_pos)
		bpy.ops.transform.rotate(value= math.radians(90), orient_axis = 'Z')
		new_pos = selected_uv_verts_pos()
		return{'FINISHED'}

class QuickRotateUv90Neg(bpy.types.Operator):
	bl_idname = "uv.rotate_90_neg"
	bl_label = "Rotate Uvs -90 degrees"
	bl_description = "Edit pivot position and scale"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		bpy.ops.transform.rotate(value= math.radians(-90), orient_axis = 'Z')
		return{'FINISHED'}