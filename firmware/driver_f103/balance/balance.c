/**
 * @file    balance.c
 * @brief   LQR 平衡控制器实现
 *
 * ============ 关键: 轮式倒立摆的 LQR 反馈符号 ============
 * 轮式倒立摆是"欠驱动耦合系统": 一个执行器 u 同时影响俯仰角 theta 和位移 x。
 * 解 LQR 黎卡提方程会发现: 四路反馈全是"正反馈"(测量值 - 设定值):
 *
 *   u_angle = +Ka*(angle - angle_zero)   (前倾 -> 前追)
 *   u_gyro  = +Kg*gyro                   (倒得越快 -> 追得越狠)
 *   u_dist  = +Kd*(distance - distance_zero)  (看似反直觉, 见下)
 *   u_speed = +Ks*(speed - speed_target)
 *
 * 为什么位移也是正反馈? 因为位移无法被直接控制, 只能"间接"稳定:
 *   x>0 (走远了) -> u=+Kd*x 加速前冲 -> 造成后仰(theta<0)
 *   -> 角度环 u_angle=Ka*theta<0 加速后退 -> x 被拉回。
 * 这就是"先造一个后仰, 再靠角度环拉回来"的耦合机理, 正是 LQR 的结论。
 *
 * (参考固件 lqr_balance_loop 注释同样写明: 这是 LQR 算式拆成 4 个 P 控制)
 *
 * 模型 (轮式倒立摆, 线性化):
 *   theta_ddot = A*theta - B*u     (u=轮子前向加速度, 前向加速 -> 后仰)
 *   x_ddot     = C*u
 */

#include "balance.h"

void balance_init(BalanceController *bc, float dt)
{
    /* 参考固件 PID 初值, 之后可在线调参 */
    pid_init(&bc->pid_angle,    1.0f, 0.0f, 0.0f, 8.0f, dt);
    pid_init(&bc->pid_gyro,     0.06f, 0.0f, 0.0f, 8.0f, dt);
    pid_init(&bc->pid_distance, 0.5f, 0.0f, 0.0f, 8.0f, dt);
    pid_init(&bc->pid_speed,    0.7f, 0.0f, 0.0f, 8.0f, dt);

    bc->angle_zero = -2.25f; /* 参考初值 (实际重心偏置) */
    bc->distance_zero = 0.0f;
    bc->output_limit = 8.0f;
    bc->prev_speed_target = 0.0f;
    bc->move_stop_flag = 0;
}

float balance_update(BalanceController *bc,
                     float angle, float gyro, float distance, float speed,
                     float speed_target)
{
    /* 0. 位移零点重置 (参考 lqr_balance_loop, 关键: 让位移环不与速度环打架)
     *   - 有运动指令时: 每周期重置位移零点, 位移环退出, 速度环接管
     *   - 运动指令复零时: 等速度降到阈值后重置位移零点 (原地停车)
     *   - 被快速推动时: 重置位移零点 (防止猛冲)
     */
    if (speed_target != 0.0f) {
        bc->distance_zero = distance;   /* 运动时位移环不干预 */
        bc->move_stop_flag = 0;
    } else {
        if (bc->prev_speed_target != 0.0f) {
            bc->move_stop_flag = 1;     /* 刚收到停止指令 */
        }
        if (bc->move_stop_flag && (speed < 0.5f && speed > -0.5f)) {
            bc->distance_zero = distance;   /* 停稳后原地保持 */
            bc->move_stop_flag = 0;
        }
    }
    if (speed > 15.0f || speed < -15.0f) {
        bc->distance_zero = distance;   /* 被快速推动 -> 原地停车 */
    }
    bc->prev_speed_target = speed_target;

    /* 1. 角度项: 正反馈
     *    pid_update(setpoint=angle, measurement=angle_zero) -> error = angle - zero */
    float angle_control = pid_update(&bc->pid_angle, angle, bc->angle_zero);

    /* 2. 角速度项: 正反馈
     *    error = gyro - 0 */
    float gyro_control = pid_update(&bc->pid_gyro, gyro, 0.0f);

    /* 3. 位移项: 正反馈 (LQR 结论, 见头注释) */
    float distance_control = pid_update(&bc->pid_distance, distance, bc->distance_zero);

    /* 4. 速度项: 正反馈 (LQR 结论) */
    float speed_control = pid_update(&bc->pid_speed, speed, speed_target);

    /* 5. 合成 LQR 输出 */
    float u = angle_control + gyro_control + distance_control + speed_control;

    /* 6. 限幅 */
    if (u > bc->output_limit)  u = bc->output_limit;
    if (u < -bc->output_limit) u = -bc->output_limit;

    return u;
}

void balance_reset(BalanceController *bc)
{
    pid_reset(&bc->pid_angle);
    pid_reset(&bc->pid_gyro);
    pid_reset(&bc->pid_distance);
    pid_reset(&bc->pid_speed);
    bc->distance_zero = 0.0f;
}
