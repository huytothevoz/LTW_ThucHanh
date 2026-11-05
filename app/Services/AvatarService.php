<?php

namespace App\Services;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;

class AvatarService
{
    public static function replace(int $userId, UploadedFile $file): string
    {
        $image = @getimagesize($file->getPathname());
        if (!$image || $image[0] !== 512 || $image[1] !== 512 || $image[2] !== IMAGETYPE_PNG) {
            throw new \DomainException('Ảnh đại diện không hợp lệ. Hãy tải ảnh đã cắt trong khung xem trước.');
        }

        $directory = self::directory();
        if (!is_dir($directory) && !mkdir($directory, 0700, true) && !is_dir($directory)) {
            throw new \RuntimeException('Could not create the avatar storage directory.');
        }

        $filename = bin2hex(random_bytes(24)).'.png';
        $destination = $directory.DIRECTORY_SEPARATOR.$filename;
        $temporary = $destination.'.tmp';
        $contents = file_get_contents($file->getPathname());
        if ($contents === false || file_put_contents($temporary, $contents, LOCK_EX) !== strlen($contents)) {
            @unlink($temporary);
            throw new \RuntimeException('Could not store the uploaded avatar.');
        }
        @chmod($temporary, 0600);
        if (!rename($temporary, $destination)) {
            @unlink($temporary);
            throw new \RuntimeException('Could not finalize the uploaded avatar.');
        }

        try {
            $oldFilename = DB::table('users')->where('id', $userId)->value('avatar_path');
            $updated = DB::table('users')->where('id', $userId)->update([
                'avatar_path' => $filename,
                'updated_at' => AccountService::now(),
            ]);
            if ($updated !== 1) {
                throw new \RuntimeException('Could not update the user avatar record.');
            }
        } catch (\Throwable $exception) {
            @unlink($destination);
            throw $exception;
        }

        $oldPath = self::path($oldFilename);
        if ($oldPath && $oldPath !== $destination && is_file($oldPath) && !unlink($oldPath)) {
            throw new \RuntimeException('The old avatar could not be removed from storage.');
        }

        return '/api/me/avatar';
    }

    public static function path(mixed $filename): ?string
    {
        if (!is_string($filename) || !preg_match('/^[a-f0-9]{48}\.png$/D', $filename)) {
            return null;
        }

        return self::directory().DIRECTORY_SEPARATOR.$filename;
    }

    private static function directory(): string
    {
        $configured = trim((string) env('AVATAR_STORAGE_PATH', ''));
        if ($configured === '') {
            return storage_path('app/avatars');
        }

        if (str_starts_with($configured, DIRECTORY_SEPARATOR)
            || preg_match('/^[A-Za-z]:[\\\\\\/]/', $configured)) {
            return $configured;
        }

        return base_path($configured);
    }
}
