/**
 * @file    foc_control.c
 * @brief   FOC 控制环对象实现
 */

#include "foc_control.h"

void foc_control_init(FocControl *fc, int pole_pairs, float dt, float lpf_alpha)
{
    fc->pole_pairs = pole_pairs;
    fc->dt = dt;
    fc->lpf_alpha = lpf_alpha;
    fc->prev_mech_angle = 0.0f;
    fc->mech_angle_accum = 0.0f;
    fc->velocity = 0.0f;
}

float foc_control_encoder_update(FocControl *fc, float mech_angle)
{
    /* 1. 角度解绕: 处理 0/2pi 跳变
     * 前提: 两次采样间角度增量 |delta| < pi (采样率足够高)。
     * 1kHz 下即使 3000 RPM 每步也只转 0.314 rad, 远小于 pi, 恒成立。
     */
    float delta = mech_angle - fc->prev_mech_angle;
    if (delta > (float)M_PI)       delta -= TWO_PI; /* 正向跨 0 点 */
    else if (delta < -(float)M_PI) delta += TWO_PI; /* 反向跨 0 点 */

    fc->mech_angle_accum += delta;
    fc->prev_mech_angle = mech_angle;

    /* 2. 速度估计: 差分 + 一阶低通 */
    float vel_raw = delta / fc->dt;
    fc->velocity += fc->lpf_alpha * (vel_raw - fc->velocity);

    /* 3. 返回电角度 */
    return fc->mech_angle_accum * (float)fc->pole_pairs;
}

DutyCycle foc_control_voltage_step(float theta_elec, float vq, float vd)
{
    /* 电压模式 FOC: dq 电压 -> 反 Park -> SVPWM */
    AlphaBeta v = inverse_park(vd, vq, theta_elec);
    return svpwm(v.alpha, v.beta);
}
