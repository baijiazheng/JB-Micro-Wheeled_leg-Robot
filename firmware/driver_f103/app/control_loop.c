/**
 * @file    control_loop.c
 * @brief   1kHz 控制环实现: 编码器 + IMU + LQR平衡 + yaw + FOC -> PWM
 *
 * 数据流 (每 1ms):
 *   AS5600(角度) -> FocControl(解绕/速度) -> 电角度 + 转速
 *   MPU6050      -> 俯仰角 + 俯仰角速度 + 偏航角速度
 *   BalanceController(LQR) -> 平衡转矩 U (俯仰)
 *   yaw 控制器 -> 差速转矩 Y (转向)
 *   FOC 电压步 -> 三相占空比 -> PWM(L6234)
 */

#include "control_loop.h"
#include "stm32f1xx_hal.h"
#include "../foc/foc_control.h"
#include "../balance/balance.h"
#include "pid.h"  /* 经 Makefile -I ../common/pid */
#include "../hal/pwm.h"
#include "../hal/as5600.h"
#include "../hal/mpu6050.h"
#include "../hal/can_bus.h"

#define POLE_PAIRS   7
#define CONTROL_DT   0.001f   /* 1kHz */

static FocControl        g_foc1;
static FocControl        g_foc2;
static BalanceController g_balance;
static As5600            g_enc1;
static As5600            g_enc2;
static Mpu6050           g_imu;
static CanBus            g_can;

/* yaw 转向控制 */
static PIDController g_yaw_angle_pid;
static PIDController g_yaw_gyro_pid;
static float g_yaw_angle;        /* 实际偏航角 (积分) */
static float g_yaw_angle_target; /* 目标偏航角 (来自 CAN 角速度指令) */

/* ---- 外部句柄 (main.c) ---- */
extern I2C_HandleTypeDef hi2c1;
extern I2C_HandleTypeDef hi2c2;
extern CAN_HandleTypeDef hcan;

void control_loop_init(void)
{
    pwm_init();
    pwm_enable(1);

    as5600_init(&g_enc1, &hi2c1);
    as5600_init(&g_enc2, &hi2c2);
    mpu6050_init(&g_imu, &hi2c2, CONTROL_DT); /* IMU 与编码器2 共 I2C2 */

    foc_control_init(&g_foc1, POLE_PAIRS, CONTROL_DT, 0.1f);
    foc_control_init(&g_foc2, POLE_PAIRS, CONTROL_DT, 0.1f);

    balance_init(&g_balance, CONTROL_DT);

    pid_init(&g_yaw_angle_pid, 1.0f, 0.0f, 0.0f, 4.0f, CONTROL_DT);
    pid_init(&g_yaw_gyro_pid,  0.04f, 0.0f, 0.0f, 4.0f, CONTROL_DT);
    g_yaw_angle = 0.0f;
    g_yaw_angle_target = 0.0f;

    can_bus_init(&g_can, &hcan);
}

void control_loop_1khz(void)
{
    /* 1. 读传感器 */
    float mech1 = as5600_read_radians(&g_enc1);
    float mech2 = as5600_read_radians(&g_enc2);
    float theta_elec1 = foc_control_encoder_update(&g_foc1, mech1);
    float theta_elec2 = foc_control_encoder_update(&g_foc2, mech2);
    mpu6050_update(&g_imu);

    /* 2. 轮部平均位移/转速 */
    float distance = 0.5f * (g_foc1.mech_angle_accum + g_foc2.mech_angle_accum);
    float speed    = 0.5f * (g_foc1.velocity + g_foc2.velocity);

    /* 3. 目标速度 + 目标偏航角速度 (来自 CAN 指令) */
    float target_speed = g_can.rx_cmd.linear_vel / 100.0f;
    float target_yaw_rate = g_can.rx_cmd.angular_vel / 100.0f; /* 度/秒 */
    if (g_can.rx_cmd.estop) {
        target_speed = 0.0f;
        target_yaw_rate = 0.0f;
        balance_reset(&g_balance);
    }

    /* 4. LQR 平衡 (俯仰) */
    float u = balance_update(&g_balance, g_imu.pitch_deg, g_imu.pitch_rate,
                             distance, speed, target_speed);

    /* 5. yaw 转向: 目标角速度积分成目标角度, 角度环 + 角速度环 */
    g_yaw_angle_target += target_yaw_rate * CONTROL_DT;
    g_yaw_angle += g_imu.yaw_rate * CONTROL_DT;
    float yaw_angle_ctrl = pid_update(&g_yaw_angle_pid, g_yaw_angle_target, g_yaw_angle);
    float yaw_gyro_ctrl  = pid_update(&g_yaw_gyro_pid, target_yaw_rate, g_imu.yaw_rate);
    float yaw = yaw_angle_ctrl + yaw_gyro_ctrl;

    /* 6. 电压 FOC: 俯仰转矩 + yaw 差速 (左轮 +yaw, 右轮 -yaw) */
    float vq1 = (u + yaw) * 0.125f;  /* U(±8) -> Vq(±1) */
    float vq2 = (u - yaw) * 0.125f;
    if (vq1 > 1.0f) vq1 = 1.0f; if (vq1 < -1.0f) vq1 = -1.0f;
    if (vq2 > 1.0f) vq2 = 1.0f; if (vq2 < -1.0f) vq2 = -1.0f;

    DutyCycle d1 = foc_control_voltage_step(theta_elec1, vq1, 0.0f);
    DutyCycle d2 = foc_control_voltage_step(theta_elec2, vq2, 0.0f);

    /* 7. 写 PWM */
    pwm_set_motor1(d1.a, d1.b, d1.c);
    pwm_set_motor2(d2.a, d2.b, d2.c);
}

void control_loop_background(void)
{
    CanStatus st;
    st.pitch_angle = (int16_t)(g_imu.pitch_deg * 100.0f);
    st.pitch_rate  = (int16_t)(g_imu.pitch_rate * 100.0f);
    st.wheel_speed = (int16_t)(0.5f * (g_foc1.velocity + g_foc2.velocity) * 100.0f);
    st.battery     = 74; /* TODO: ADC 采样 */
    st.flags       = 0;

    can_bus_send_status(&g_can, &st);
}

/* ---- CAN 接收回调 (由中断调用) ---- */
void control_loop_on_can_rx(const uint8_t data[8])
{
    can_bus_on_rx(&g_can, data);
}
