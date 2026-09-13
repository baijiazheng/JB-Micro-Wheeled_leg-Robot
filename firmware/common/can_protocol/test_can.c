/**
 * @file    test_can.c
 * @brief   CAN 协议编解码 PC 端测试
 *
 * 编译: gcc -o test_can test_can.c can_protocol.c
 * 验证: 打包 -> 解包 往返一致, 含负数和边界值
 */

#include <stdio.h>
#include <string.h>
#include "can_protocol.h"

static int g_fail = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("  [FAIL] "); printf(__VA_ARGS__); printf("\n"); g_fail++; } \
    else         { printf("  [ OK ] "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

int main(void)
{
    printf("========== CAN 协议测试 ==========\n\n");

    /* ---- 1. 指令帧往返 ---- */
    printf("[1] 指令帧编解码往返\n");
    {
        CanCommand src = { -1234, 567, 80, 1, 1, 0 };
        uint8_t data[8] = {0};
        CanCommand dst;
        can_encode_command(&src, data);
        can_decode_command(data, &dst);
        CHECK(dst.linear_vel == src.linear_vel && dst.angular_vel == src.angular_vel &&
              dst.height == src.height && dst.mode == src.mode &&
              dst.jump == src.jump && dst.estop == src.estop,
              "指令往返一致 (lin=%d ang=%d h=%d mode=%d jump=%d)", 
              dst.linear_vel, dst.angular_vel, dst.height, dst.mode, dst.jump);
    }

    /* ---- 2. 状态帧往返 ---- */
    printf("\n[2] 状态帧编解码往返\n");
    {
        CanStatus src = { -225, 1234, -9999, 78, STATUS_FLAG_AIRBORNE };
        uint8_t data[8] = {0};
        CanStatus dst;
        can_encode_status(&src, data);
        can_decode_status(data, &dst);
        CHECK(dst.pitch_angle == src.pitch_angle && dst.pitch_rate == src.pitch_rate &&
              dst.wheel_speed == src.wheel_speed && dst.battery == src.battery &&
              dst.flags == src.flags,
              "状态往返一致 (pitch=%d rate=%d speed=%d bat=%d flags=0x%02x)",
              dst.pitch_angle, dst.pitch_rate, dst.wheel_speed, dst.battery, dst.flags);
    }

    /* ---- 3. 负数边界 (int16 最小值) ---- */
    printf("\n[3] 边界值 (int16 极值)\n");
    {
        CanCommand src = { -32768, 32767, 0, 0, 0, 0 };
        uint8_t data[8] = {0};
        CanCommand dst;
        can_encode_command(&src, data);
        can_decode_command(data, &dst);
        CHECK(dst.linear_vel == -32768 && dst.angular_vel == 32767,
              "int16 极值往返一致 (%d, %d)", dst.linear_vel, dst.angular_vel);
    }

    /* ---- 4. 字节序检查 (小端: -1234 = 0xFB2E -> data[0]=0x2E, data[1]=0xFB) ---- */
    printf("\n[4] 字节序检查 (小端)\n");
    {
        CanCommand src = { -1234, 0, 0, 0, 0, 0 };
        uint8_t data[8] = {0};
        can_encode_command(&src, data);
        CHECK(data[0] == 0x2E && data[1] == 0xFB,
              "小端打包正确 (data[0]=0x%02X data[1]=0x%02X)", data[0], data[1]);
    }

    printf("\n========================================\n");
    if (g_fail == 0) { printf("全部测试通过 ✅\n"); return 0; }
    else { printf("%d 项失败 ❌\n", g_fail); return 1; }
}
