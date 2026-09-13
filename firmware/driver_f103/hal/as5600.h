/**
 * @file    as5600.h
 * @brief   AS5600 磁编码器 I2C 驱动
 *
 * AS5600 固定地址 0x36, 12 位角度 (0~4095 对应 0~360°)。
 * 两个编码器必须各占一条 I2C 总线 (地址相同)。
 *
 * 关键寄存器:
 *   RAW ANGLE (0x0C): 12 位原始角度
 */

#ifndef AS5600_H
#define AS5600_H

#include <stdint.h>

#define AS5600_I2C_ADDR      0x36u
#define AS5600_REG_RAW_ANGLE 0x0Cu

typedef struct {
    void *hi2c;  /* I2C_HandleTypeDef* (用 void* 避免强耦合) */
} As5600;

/** 绑定 I2C 句柄 */
void as5600_init(As5600 *enc, void *hi2c);

/** 读原始角度 (0~4095) */
int as5600_read_raw(const As5600 *enc);

/** 读角度为机械弧度 (0 ~ 2pi) */
float as5600_read_radians(const As5600 *enc);

#endif /* AS5600_H */
