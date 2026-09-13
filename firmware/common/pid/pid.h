/**
 * @file    pid.h
 * @brief   位置式 PID 控制器 (含积分抗饱和 + 输出限幅)
 *
 * 参考固件的 LQR 平衡被拆成 4 个 PID (角度/角速度/位移/速度) 便于调参，
 * 本模块就是那个 PID 的干净实现。F103 平衡环和 F407 腿部都用它。
 *
 * 特性:
 *   - 位置式: u = Kp*e + Ki*∫e dt + Kd*de/dt
 *   - 积分限幅 (anti-windup): 输出饱和时不再累计积分
 *   - 输出限幅: |u| <= output_limit
 *   - 微分可选"对测量值"或"对误差"(默认对误差, 与 simpleFOC 一致)
 */

#ifndef PID_H
#define PID_H

#include <stdint.h>

typedef struct {
    float kp;
    float ki;
    float kd;

    float output_limit;   /* 输出绝对值上限 */
    float integral_limit; /* 积分项绝对值上限 */

    float dt;             /* 控制周期(秒), 用于 I/D 的离散化 */

    /* 内部状态 */
    float integral;
    float prev_error;
    float prev_measurement;
    uint8_t derivative_on_measurement; /* 1=对测量值微分(抗微分冲击) */
} PIDController;

/**
 * 初始化 PID。
 * @param dt 控制周期(秒)。积分/微分据此离散化。
 */
void pid_init(PIDController *pid, float kp, float ki, float kd,
              float output_limit, float dt);

/**
 * 执行一次 PID 计算。
 * @param setpoint     目标值
 * @param measurement  当前测量值
 * @return 控制输出 (已限幅)
 */
float pid_update(PIDController *pid, float setpoint, float measurement);

/** 清零积分与历史误差 (模式切换/跳跃恢复时用) */
void pid_reset(PIDController *pid);

#endif /* PID_H */
