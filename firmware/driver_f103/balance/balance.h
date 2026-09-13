/**
 * @file    balance.h
 * @brief   LQR 平衡控制器 (参考固件 lqr_balance_loop 的移植)
 *
 * 参考固件把 LQR 平衡算式拆成 4 个 PID, 便于实时调参:
 *   U = k1*(angle - angle_zero) + k2*gyro + k3*(distance - distance_zero) + k4*speed
 *     = angle_control + gyro_control + distance_control + speed_control
 *
 * 其中:
 *   angle    = 俯仰角 (IMU 的 pitch, 度)
 *   gyro     = 俯仰角速度 (度/秒)
 *   distance = 轮部平均位移 (编码器角度累加)
 *   speed    = 轮部平均转速 (编码器角速度)
 *
 * 本模块把 4 个 PID 封装成一个平衡控制器, 输出平衡转矩 U (归一化 [-limit, limit])。
 */

#ifndef BALANCE_H
#define BALANCE_H

#include "../../common/pid/pid.h"

typedef struct {
    PIDController pid_angle;    /* 角度环 */
    PIDController pid_gyro;     /* 角速度环 */
    PIDController pid_distance; /* 位移环 */
    PIDController pid_speed;    /* 速度环 */

    float angle_zero;     /* 平衡点偏置 (重心自适应, 参考初值 -2.25 度) */
    float distance_zero;  /* 位移零点 (运动指令变化时重置) */

    float output_limit;   /* 输出转矩限幅 (参考 .limit=8) */

    /* 位移零点重置状态 (参考 lqr_balance_loop) */
    float prev_speed_target;  /* 上一周期目标速度 */
    uint8_t move_stop_flag;   /* 运动指令复零时的原地停车标志 */
} BalanceController;

/**
 * 初始化平衡控制器。
 * @param dt 控制周期(秒), 建议 1kHz -> 0.001
 */
void balance_init(BalanceController *bc, float dt);

/**
 * 执行一次平衡计算。
 * @param angle    当前俯仰角 (度)
 * @param gyro     当前俯仰角速度 (度/秒)
 * @param distance 当前轮部平均位移
 * @param speed    当前轮部平均转速
 * @param speed_target 目标速度 (摇杆输入, 前进为正)
 * @return 平衡转矩 U (已限幅)
 */
float balance_update(BalanceController *bc,
                     float angle, float gyro, float distance, float speed,
                     float speed_target);

/** 复位所有 PID 与位移零点 (模式切换/倒地恢复时用) */
void balance_reset(BalanceController *bc);

#endif /* BALANCE_H */
