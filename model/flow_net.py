
"""Builds the ring network.

Summary of available functions:

  # Compute pics of the simulation runnig.
  
  # Create a graph to train on.
"""


import tensorflow as tf
import numpy as np
import flow_architecture
import input.flow_input as flow_input
import utils.boundary_utils as boundary_utils
import lb_solver as lb

FLAGS = tf.app.flags.FLAGS

# Constants describing the training process and model.

# Training params
tf.app.flags.DEFINE_string('base_dir_flow', '../checkpoints_flow',
                            """dir to store trained flow net """)
tf.app.flags.DEFINE_string('base_dir_boundary', '../checkpoints_boundary',
                            """dir to store trained net boundary """)
tf.app.flags.DEFINE_integer('batch_size', 8,
                            """ training batch size """)
tf.app.flags.DEFINE_integer('max_steps',  50000,
                            """ max number of steps to train """)
tf.app.flags.DEFINE_float('keep_prob', 1.0,
                            """ keep probability for dropout """)
tf.app.flags.DEFINE_float('learning_rate', 5e-4,
                            """ keep probability for dropout """)

# model params flow
tf.app.flags.DEFINE_string('model', 'res',
                           """ model name to train """)
tf.app.flags.DEFINE_integer('nr_res_blocks', 1,
                           """ nr res blocks """)
tf.app.flags.DEFINE_bool('gated_res', True,
                           """ gated resnet or not """)
tf.app.flags.DEFINE_string('nonlinearity', 'concat_elu',
                           """ nonlinearity used such as concat_elu, elu, concat_relu, relu """)

# model params boundary
tf.app.flags.DEFINE_integer('nr_boundary_params', 39,
                            """ number of boundary paramiters """)

# test params
tf.app.flags.DEFINE_string('test_set', "car",
                            """ either car or random """)

def inputs_flow(batch_size):
  """makes input vector
  Return:
    x: input vector, may be filled 
  """
  boundary, sflow = flow_input.flow_inputs(batch_size)
  return boundary, sflow 

def inputs_bounds(input_dims, batch_size):
  """makes input vector
  Return:
    x: input vector, may be filled 
  """
  length_input = tf.placeholder(tf.float32, [batch_size, input_dims])
  boundary = tf.placeholder(tf.float32, [batch_size, 128, 256, 1])
  tf.summary.image('boundarys', boundary)
  return length_input, boundary

def feed_dict_bounds(input_dims, batch_size):
  shape = [128, 256]
  length_input = np.random.rand(batch_size, input_dims)
  boundarys = []
  for i in xrange(batch_size):
    boundarys.append(boundary_utils.make_boundary_circle(length_input[i], shape))
  boundarys = np.expand_dims(boundarys, axis=0)
  boundarys = np.concatenate(boundarys)
  boundarys = np.expand_dims(boundarys, axis=3)
  return length_input, boundarys

def inference_flow(boundary, keep_prob):
  """Builds network.
  Args:
    inputs: input to network 
    keep_prob: dropout layer
  """
  with tf.variable_scope("flow_network") as scope:
    if FLAGS.model == "res": 
      sflow_p = flow_architecture.conv_res(boundary, nr_res_blocks=FLAGS.nr_res_blocks, keep_prob=keep_prob, nonlinearity_name=FLAGS.nonlinearity, gated=FLAGS.gated_res)
  return sflow_p

def inference_bounds(length_input):
  with tf.variable_scope("boundary_network") as scope:
    boundary = flow_architecture.fc_conv(length_input)
  tf.summary.image('boundarys_g', boundary)
  return boundary

def loss_flow(sflow_p, boundary, u_in, seq_length, density=1.0, tau=1.0):
  sflow_p_out = lb.lbm_seq(sflow_p, boundary, u_in, seq_length, density=density, tau=tau)
  loss = tf.nn.l2_loss(sflow_p - sflow_p_out)
  tf.summary.scalar('loss', loss)
  return loss

def loss_bounds(true_boundary, generated_boundary):
  intersection = tf.reduce_sum(generated_boundary * true_boundary)
  loss = -(2. * intersection + 1.) / (tf.reduce_sum(true_boundary) + tf.reduce_sum(generated_boundary) + 1.)
  #loss = tf.nn.l2_loss(true_boundary - generated_boundary)
  tf.summary.scalar('loss', loss)
  return loss

def train(total_loss, lr, global_step=None, variables=None):
   if variables is None and global_step is None:
     train_op = tf.train.AdamOptimizer(lr).minimize(total_loss)
   elif variables is None and global_step is not None:
     train_op = tf.train.AdamOptimizer(lr).minimize(total_loss,global_step)
   else:
     train_op = tf.train.GradientDescentOptimizer(lr).minimize(total_loss, var_list=variables)
   return train_op

