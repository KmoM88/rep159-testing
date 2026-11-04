#include <iostream>
#include <gz/math/Vector3.hh>
#include <gz/math/Pose3.hh>
#include <gz/math/Quaternion.hh>

int main(int argc, char** argv) {
    std::cout << "=================================================================" << std::endl;
    std::cout << " REP-159 Real-World Topology Test: Gazebo Harmonic + ROS 2 Node  " << std::endl;
    std::cout << "=================================================================" << std::endl;

    // Utilize Gazebo Harmonic gz-math7 core types
    gz::math::Vector3d pos(1.5, 2.5, 3.5);
    gz::math::Quaterniond rot(0.0, 0.7071068, 0.0, 0.7071068);
    gz::math::Pose3d pose(pos, rot);

    std::cout << " [Gazebo Math] Translation Vector: " << pose.Pos() << std::endl;
    std::cout << " [Gazebo Math] Orientation Quaternion: "
              << "w=" << pose.Rot().W() << " x=" << pose.Rot().X()
              << " y=" << pose.Rot().Y() << " z=" << pose.Rot().Z() << std::endl;
    std::cout << " [Gazebo Math] Euler Angles (RPY): "
              << pose.Rot().Roll() << " rad, "
              << pose.Rot().Pitch() << " rad, "
              << pose.Rot().Yaw() << " rad" << std::endl;

    gz::math::Vector3d local_offset(1.0, 0.0, 0.0);
    gz::math::Vector3d transformed = pose.Rot().RotateVector(local_offset) + pose.Pos();
    std::cout << " [Gazebo Math] Transformed Offset Vector: " << transformed << std::endl;

    std::cout << "-----------------------------------------------------------------" << std::endl;
    std::cout << " [SUCCESS] Gazebo Harmonic core libraries successfully linked!   " << std::endl;
    std::cout << "=================================================================" << std::endl;
    return 0;
}
