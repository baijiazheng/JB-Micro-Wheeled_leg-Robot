/**
 * @file    pwm.h
 * @brief   L6234 三相 PWM 驱动 (TIM1 + TIM3, 电压模式 FOC 输出)
 *
 * 每个 L6234 需要 3 路 PWM (IN1/IN2/IN3) + 1 路使能 (EN)。
 * 这里用两个定时器各出 3 路 PWM:
 *   TIM1: PA8/PA9/PA10 -> 电机1
 *   TIM3: PA6/PA7/PB0  -> 电机2
 *
 * SVPWM 输出的占空比 [0,1] 直接映射到 TIM 比较寄存器 (0 ~ ARR)。
 */

#ifndef PWM_H
#define PWM_H

#include <stdint.h>

/** 初始化两路电机的三相 PWM (频率 20kHz) */
void pwm_init(void);

/** 设置电机1三相占空比 (0.0 ~ 1.0) */
void pwm_set_motor1(float duty_a, float duty_b, float duty_c);

/** 设置电机2三相占空比 (0.0 ~ 1.0) */
void pwm_set_motor2(float duty_a, float duty_b, float duty_c);

/** 电机使能 (L6234 EN 引脚) */
void pwm_enable(uint8_t en);

#endif /* PWM_H */
