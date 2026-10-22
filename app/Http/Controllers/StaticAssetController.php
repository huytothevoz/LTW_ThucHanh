<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class StaticAssetController
{
    public function __invoke(Request $request, string $path): Response
    {
        $root = realpath(base_path('static'));
        $file = realpath(base_path('static/'.str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $path)));

        if (!$root || !$file || !str_starts_with($file, $root.DIRECTORY_SEPARATOR) || !is_file($file)) {
            abort(404);
        }

        $contentType = match (strtolower(pathinfo($file, PATHINFO_EXTENSION))) {
            'css' => 'text/css; charset=UTF-8',
            'js' => 'text/javascript; charset=UTF-8',
            'svg' => 'image/svg+xml',
            default => 'application/octet-stream',
        };

        return response()->file($file, [
            'Cache-Control' => 'public, max-age=3600',
            'Content-Type' => $contentType,
            'X-Content-Type-Options' => 'nosniff',
        ]);
    }
}
