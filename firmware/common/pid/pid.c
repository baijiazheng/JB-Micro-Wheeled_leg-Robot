/**
 * @file    pid.c
 * @brief   位置式 PID 实现
 *
 * 离散化 (后向欧拉):
 *   积分: integral += error * dt
 *   微分: derivative = (error - prev_error) / dt   (对误差)
 *   或:   derivative = -(measurement - prev_measurement) / dt  (对测量值)
 */

#include "pid.h"

void pid_init(PIDController *pid, float kp, float ki, float kd,
              float output_limit, float dt)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->output_limit = output_limit;
    pid->integral_limit = output_limit; /* 默认积分限幅 = 输出限幅 */
    pid->dt = dt;
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->prev_measurement = 0.0f;
    pid->derivative_on_measurement = 0; /* 默认对误差微分 (同 simpleFOC) */
}

float pid_update(PIDController *pid, float setpoint, float measurement)
{
    float error = setpoint - measurement;

    /* 1. 比例项 */
    float p = pid->kp * error;

    /* 2. 积分项 (含抗饱和: 只有输出未饱和时才累计) */
    float i = pid->integral + pid->ki * error * pid->dt;

    /* 3. 微分项 */
    float d;
    if (pid->derivative_on_measurement) {
        d = -pid->kd * (measurement - pid->prev_measurement) / pid->dt;
    } else {
        d = pid->kd * (error - pid->prev_error) / pid->dt;
    }

    /* 4. 合成 + 限幅 */
    float u = p + i + d;
    if (u > pid->output_limit) {
        u = pid->output_limit;
    } else if (u < -pid->output_limit) {
        u = -pid->output_limit;
    }

    /* 5. 抗饱和: 输出被限幅时冻结积分 (clamping) */
    if (u == pid->output_limit || u == -pid->output_limit) {
        /* 不更新积分: 保持 pid->integral 不变 */
    } else {
        /* 积分限幅后更新 */
        float clamped_i = i;
        if (clamped_i > pid->integral_limit)  clamped_i = pid->integral_limit;
        if (clamped_i < -pid->integral_limit) clamped_i = -pid->integral_limit;
        pid->integral = clamped_i;
    }

    /* 6. 保存历史 */
    pid->prev_error = error;
    pid->prev_measurement = measurement;

    return u;
}

void pid_reset(PIDController *pid)
{
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->prev_measurement = 0.0f;
}
