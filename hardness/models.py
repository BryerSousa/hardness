import numpy as np
import pandas as pd
#from argiope import mesh as Mesh
import argiope, hardness
import os, subprocess, inspect
from string import Template

# PATH TO MODULE
import hardness
MODPATH = os.path.dirname(inspect.getfile(hardness))


################################################################################
# MODEL DEFINITION
################################################################################
class Indentation2D(argiope.models.Model):
  """
  2D indentation class.
  """
    
  def write_input(self):
    """
    Writes the input file in the chosen format.
    """
    hardness.models.indentation_2D_input(sample_mesh   = self.meshes["sample"],
                                   indenter_mesh = self.meshes["indenter"],
                                   steps = self.steps,
                                   materials = self.materials,
                                   solver = self.solver,
                                   path = "{0}/{1}.inp".format(self.workdir,
                                                               self.label))
                                   
                                   
    
  def write_postproc(self):
    """
    Writes the prosproc scripts
    """
    if self.solver == "abaqus":
      hardness.postproc.indentation_abqpostproc(
          path = "{0}/{1}_abqpp.py".format(
              self.workdir,
              self.label),
          label = self.label,    
          solver= self.solver)

################################################################################
# MESH PROCESSING
################################################################################
def process_2D_mesh(mesh, element_map, material_map):
  """
  Processes a 2D mesh, indenter or sample
  """
  mesh.elements[("sets", "ALL_ELEMENTS", mesh._null)] = True
  mesh.nodes[("sets", "ALL_NODES")] = True
  mesh.element_set_to_node_set(tag = "SURFACE")
  mesh.element_set_to_node_set(tag = "BOTTOM")
  mesh.element_set_to_node_set(tag = "AXIS")
  del mesh.elements[("sets", "SURFACE", "x")]
  del mesh.elements[("sets", "BOTTOM", "x")]
  del mesh.elements[("sets", "AXIS", "x")]
  mesh.elements = mesh.elements.loc[mesh.space() == 2] 
  mesh.node_set_to_surface("SURFACE")
  mesh = element_map(mesh)
  mesh = material_map(mesh)
  return mesh                                      


def process_2D_indenter(mesh, rigid = True, **kwargs):
  """
  Processes a raw gmsh 2D indenter mesh 
  """
  mesh = process_2D_mesh(mesh, **kwargs)
  x, y = mesh.nodes.coords.x.values, mesh.nodes.coords.y.values
  mesh.nodes[("sets","TIP_NODE")] = (x == 0) * (y == 0)
  mesh.nodes[("sets","REF_NODE")] = (x == 0) * (y == y.max())
  if rigid == False:
    mesh.nodes.loc[:, ("sets", "RIGID_NODES")] = (
         mesh.nodes.sets["BOTTOM"])
  else: 
    mesh.nodes.loc[:, ("sets", "RIGID_NODES")] = (
         mesh.nodes.sets["ALL_NODES"])
  return mesh        
################################################################################
# SAMPLE MESH 2D
################################################################################
def sample_mesh_2D(gmsh_path = "gmsh", 
                   workdir = "./", 
                   lx = 1., ly = 1., 
                   r1 = 2., r2 = 1000., 
                   Nx = 32, Ny = 32,
                   Nr = 16, Nt = 8, 
                   geoPath = "sample_mesh_2D", 
                   algorithm = "delquad",
                   **kwargs):
  """
  Builds an indentation mesh.
  """
  q1 = (r2/r1)**(1./Nr) 
  lcx, lcy = lx / Nx, ly / Ny
  geo = Template(
        open(MODPATH + "/templates/models/indentation_2D/indentation_mesh_2D.geo").read())
  geo = geo.substitute(
        lx = lx,
        ly = ly,
        r1 = r1,
        r2 = r2,
        Nx = Nx,
        Ny = Ny,
        Nr = Nr,
        Nt = Nt,
        q1 = q1)
  open(workdir + geoPath + ".geo", "w").write(geo)
  p = subprocess.Popen("{0} -2 -algo {1} {2}".format(gmsh_path, 
                                                     algorithm,
                                                     geoPath + ".geo"), 
                       cwd = workdir, shell=True, stdout = subprocess.PIPE)  
  trash = p.communicate()
  mesh = argiope.mesh.read_msh(workdir + geoPath + ".msh")
  return process_2D_mesh(mesh, **kwargs)


################################################################################
# INDENTERS
################################################################################  



def conical_indenter_mesh_2D(gmsh_path, workdir, psi= 70.29, 
                             r1 = 1., r2 = 10., r3 = 100., 
                             lc1 = 0.1, lc2 = 20., 
                             rigid = False, 
                             geoPath = "conical_indenter_2D", 
                             algorithm = "delquad", 
                             **kwargs):
  """
  Builds a conical indenter mesh.
  """
  # Some high lvl maths...
  psi = np.radians(psi)
  x2 = r3 * np.sin(psi)
  y2 = r3 * np.cos(psi)
  y3 = r3 
  # Template filling  
  geo = Template(
        open(MODPATH + "/templates/models/indentation_2D/conical_indenter_mesh_2D.geo").read())
  geo = geo.substitute(
    lc1 = lc1,
    lc2 = lc2,
    r1  = r1,
    r2  = r2,
    x2  = x2,
    y2  = y2,
    y3  = y3)
  open(workdir + geoPath + ".geo", "w").write(geo)
  p = subprocess.Popen("{0} -2 -algo {1} {2}".format(gmsh_path, 
                                                     algorithm,
                                                     geoPath + ".geo"), 
                       cwd = workdir, shell=True, stdout = subprocess.PIPE)
  trash = p.communicate()
  return process_2D_indenter(mesh, **kwargs)
 

def spheroconical_indenter_mesh_2D(gmsh_path, workdir, psi= 70.29, R = 1., 
                                   r1 = 1., r2 = 10., r3 = 100., 
                                   lc1 = 0.1, lc2 = 20., 
                                   geoPath = "spheroconical_indenter_2D", 
                                   algorithm = "delquad", 
                                   **kwargs):
  """
  Builds a spheroconical indenter mesh.
  """
  # Some high lvl maths...
  psi = np.radians(psi)
  x2 = R  * np.cos(psi)
  y2 = R  * (1. - np.sin(psi))
  x3 = r3 * np.sin(psi)
  dh = R * (1. / np.sin(psi) - 1.)
  y3 = r3 * np.cos(psi) - dh
  y4 = r3 - dh
  y5 = R 
  y6 = -dh
  # Template filling  
  geo = Template(
        open(MODPATH + "/templates/models/indentation_2D/spheroconical_indenter_mesh_2D.geo").read())
  geo = geo.substitute(
     lc1 = lc1,
     lc2 = lc2,
     r1 = r1,
     r2 = r2,
     x2 = x2,
     y2 = y2,
     x3 = x3,
     y3 = y3,
     y4 = y4,
     y5 = y5,
     y6 = y6)
  open(workdir + geoPath + ".geo", "w").write(geo)
  p = subprocess.Popen("{0} -2 -algo {1} {2}".format(gmsh_path, 
                                                     algorithm,
                                                     geoPath + ".geo"), 
                       cwd = workdir, shell=True, stdout = subprocess.PIPE)
  trash = p.communicate()
  mesh = argiope.mesh.read_msh(workdir + geoPath + ".msh")
  """
  mesh.elements[("sets", "ALL_ELEMENTS", mesh._null)] = True
  mesh.element_set_to_node_set(tag = "SURFACE")
  mesh.element_set_to_node_set(tag = "BOTTOM")
  mesh.element_set_to_node_set(tag = "AXIS")
  mesh.elements.drop(("sets", "SURFACE", mesh._null), 1)
  mesh.elements.drop(("sets", "BOTTOM", mesh._null), 1)
  mesh.elements.drop(("sets", "AXIS", mesh._null), 1)
  mesh.elements = mesh.elements.loc[mesh.space() == 2] 
  mesh.node_set_to_surface("SURFACE")
  if rigid == False:
    mesh.nodes.loc[:, ("sets", "RIGID_NODES", mesh._null)] = (
         mesh.nodes.sets["BOTTOM"])
  else: 
    mesh.nodes.loc[:, ("sets", "RIGID_NODES", mesh._null)] = (
         mesh.nodes.sets["ALL_ELEMENTS"])
  x, y = mesh.nodes.coords.x.values, mesh.nodes.coords.y.values
  m.nodes[("sets","TIP_NODE")] = (x == 0) * (y == 0)
  m.nodes[("sets","TIP_NODE")] = (x == 0) * (y == y.max())
  if element_map == None: element_map = {"tri3": "CAX3", "quad4": "CAX4"}
  for etype, group in mesh.elements.groupby((("type", "argiope", mesh._null),)):
    if etype in element_map.keys():
      mesh.elements.loc[group.index, ("type", "solver", 
                                        mesh._null)] = element_map[etype]
  # materials
  mesh.elements.materials = "SAMPLE_MAT"  
  return mesh
  """
  return process_2D_indenter(mesh, **kwargs)    

  
################################################################################
# 2D STEP
################################################################################  
def indentation_2D_step_input(control_type = "disp", 
                              name = "STEP", 
                              duration = 1., 
                              nframes = 100,
                              kind = "fixed", 
                              controlled_value = .1,
                              min_frame_duration = 1.e-8,
                              solver = "abaqus"):
  rootPath = "/templates/models/indentation_2D/steps/"
  if solver == "abaqus":
    if kind == "fixed":
      if control_type == "disp":
        pattern = rootPath + "indentation_2D_step_disp_control_fixed.inp"
      if control_type == "force":
        pattern = rootPath + "indentation_2D_step_load_control_fixed.inp"  
      pattern = Template(open(MODPATH + pattern).read())
              
      return pattern.substitute(NAME = name,
                               CONTROLLED_VALUE = controlled_value,
                               DURATION = duration,
                               FRAMEDURATION = float(duration) / nframes, )
    if kind == "adaptative":
      if control_type == "disp":
        pattern = rootPath + "indentation_2D_step_disp_control_adaptative.inp"
      if control_type == "force":
        pattern = rootPath + "indentation_2D_step_load_control_adaptative.inp"  
      pattern = Template(open(MODPATH + pattern).read())
              
      return pattern.substitute(NAME = name,
                               CONTROLLED_VALUE = controlled_value,
                               DURATION = duration,
                               FRAMEDURATION = float(duration) / nframes, 
                               MINFRAMEDURATION = min_frame_duration)                           

################################################################################
# 2D ABAQUS INPUT FILE
################################################################################  
def indentation_2D_input(sample_mesh, 
                         indenter_mesh,
                         steps, 
                         materials,
                         path = None, 
                         element_map = None, 
                         solver = "abaqus"):
  """
  Returns a indentation input file.
  """
  if solver == "abaqus":
    pattern = Template(
        open(MODPATH + "/templates/models/indentation_2D/indentation_2D.inp")
        .read())
    
    pattern = pattern.substitute(
        SAMPLE_MESH = sample_mesh.write_inp(),
        INDENTER_MESH = indenter_mesh.write_inp(),
        STEPS = "".join(steps),
        MATERIALS = "\n".join([m.write_inp() for m in materials]) )
  if path == None:            
    return pattern
  else:
    open(path, "w").write(pattern)  
