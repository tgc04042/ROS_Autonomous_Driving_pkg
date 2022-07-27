# ROS_Autonomous_Driving_pkg

# Sub Project Lists (meaning submodules)
All sub Projects are in **src** directory
- 

# Installation
### Build workspace
When you clone this repository for the first time, You need to build workspace as follow.

#### particle filter geometry/tf2
$pip3 install pyyaml==5.4.1
$wstool init
$wstool set -y src/geometry2 --git  https://github.com/ros/geometry2  -v 0.6.5
$wstool up
$rosdep install --from-paths src --ignore-src -y -r
$catkin_make --cmake-args -DCMAKE_BUILD_TYPE=Release -DPYTHON_EXECUTABLE=/usr/bin/python3 -DPYTHON_INCLUDE_DIR=/usr/include/python3.6m -DPYTHON_LIBRARY=/usr/lib/aarch64-linux-gnu/libpython3.6m.so
```
#in the your workspace
$catkin_make
```

This is Test
