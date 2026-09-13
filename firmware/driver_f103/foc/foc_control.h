/**
 * @file    foc_control.h
 * @brief   FOC 控制环对象 (硬件无关, 可 PC 仿真)
 *
 * 职责:
 *   1. 编码器角度解绕 (unwrap) + 速度估计 (AS5600 机械角 -> 连续角度/角速度)
 *   2. 电压模式 FOC 一步: 电角度 + Vq -> 三相占空比
 *
 * 与 foc_math.c 的关系: foc_math 是纯数学, 本模块是"控制对象"——
 * 维护状态(角度/速度)并调用 foc_math 完成一次 FOC 计算。
 *
 * 极对数: 参考固件 BLDCMotor(7) -> 7 对极 (14 极)。
 * 电角度 = 机械角度 x 极对数。
 */

#ifndef FOC_CONTROL_H
#define FOC_CONTROL_H

#include "foc_math.h"

typedef struct {
    int   pole_pairs;        /* 极对数 (参考电机 = 7) */
    float dt;                /* 控制周期 (秒) */

    /* 速度估计状态 */
    float lpf_alpha;         /* 速度低通系数 [0,1], 越大越灵敏 */
    float prev_mech_angle;   /* 上一次机械角 (rad) */
    float mech_angle_accum;  /* 连续(解绕后)机械角 (rad) */
    float velocity;          /* 估算机械角速度 (rad/s) */
} FocControl;

/**
 * 初始化 FOC 控制对象。
 * @param pole_pairs 极对数
 * @param dt         控制周期(秒), 如 1kHz 则 0.001
 * @param lpf_alpha  速度低通系数, 建议 0.05~0.2
 */
void foc_control_init(FocControl *fc, int pole_pairs, float dt, float lpf_alpha);

/**
 * 编码器更新: 输入 AS5600 机械角(0..2pi), 更新速度估计。
 * @return 当前电角度 (rad), 已按极对数放大
 */
float foc_control_encoder_update(FocControl *fc, float mech_angle);

/**
 * 电压模式 FOC 一步。
 * @param vq  q 轴目标电压 (归一化 [-1,1]), 即扭矩/转速指令
 * @param vd  d 轴目标电压 (通常 0)
 * @return 三相占空比 [0,1]
 */
DutyCycle foc_control_voltage_step(float theta_elec, float vq, float vd);

#endif /* FOC_CONTROL_H */
