import SwiftUI
import SafariServices
import AuthenticationServices
import AVKit
import AVFoundation

// MARK: - Native UIKit Wrappers (ASWebAuthenticationSession, SFSafariViewController & Share Sheet)

struct IdentifiableURL: Identifiable, Equatable {
    var id: String { url.absoluteString }
    let url: URL
}

@MainActor
final class GoogleWebAuthCoordinator: NSObject, ASWebAuthenticationPresentationContextProviding {
    static let shared = GoogleWebAuthCoordinator()
    private var activeSession: ASWebAuthenticationSession?

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        let scenes = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .sorted { a, _ in a.activationState == .foregroundActive }
        for scene in scenes {
            if let keyWin = scene.windows.first(where: { $0.isKeyWindow }) {
                return keyWin
            }
            if let anyWin = scene.windows.first {
                return anyWin
            }
        }
        return ASPresentationAnchor()
    }

    func authenticate(url: URL, callbackScheme: String) async throws -> URL {
        activeSession?.cancel()
        return try await withCheckedThrowingContinuation { continuation in
            var resumed = false
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: callbackScheme) { [weak self] callbackURL, error in
                Task { @MainActor in
                    self?.activeSession = nil
                    guard !resumed else { return }
                    resumed = true
                    if let callbackURL {
                        continuation.resume(returning: callbackURL)
                    } else if let error {
                        continuation.resume(throwing: error)
                    } else {
                        continuation.resume(throwing: ColabBridgeError.invalidResponse(L("未收到 Google 授权回调", "No Google OAuth callback received")))
                    }
                }
            }
            session.presentationContextProvider = self
            // Share iOS Safari cookies so already-signed-in Google accounts appear immediately without re-typing email/2FA
            session.prefersEphemeralWebBrowserSession = false
            self.activeSession = session
            if !session.start() {
                self.activeSession = nil
                if !resumed {
                    resumed = true
                    continuation.resume(throwing: ColabBridgeError.invalidResponse(L("无法拉起系统 Google 安全登录窗口", "Failed to start ASWebAuthenticationSession")))
                }
            }
        }
    }
}

struct SafariSheetView: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let cfg = SFSafariViewController.Configuration()
        cfg.entersReaderIfAvailable = false
        let vc = SFSafariViewController(url: url, configuration: cfg)
        vc.dismissButtonStyle = .done
        return vc
    }

    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {}
}

struct ActivityShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

@MainActor
func presentSystemShareSheet(items: [Any]) {
    let scenes = UIApplication.shared.connectedScenes
        .compactMap { $0 as? UIWindowScene }
        .sorted { a, _ in a.activationState == .foregroundActive }
    guard let window = scenes.lazy.compactMap({ scene in
        scene.windows.first(where: { $0.isKeyWindow }) ?? scene.windows.first
    }).first,
    var topVC = window.rootViewController else {
        return
    }
    while let presented = topVC.presentedViewController {
        if presented is UIActivityViewController {
            return
        }
        topVC = presented
    }
    let activityVC = UIActivityViewController(activityItems: items, applicationActivities: nil)
    if let popover = activityVC.popoverPresentationController {
        popover.sourceView = topVC.view
        popover.sourceRect = CGRect(
            x: topVC.view.bounds.midX,
            y: topVC.view.bounds.midY,
            width: 1,
            height: 1
        )
        popover.permittedArrowDirections = []
    }
    topVC.present(activityVC, animated: true)
}

struct ClippedVideoPlayerView: UIViewControllerRepresentable {
    let player: AVPlayer?

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let vc = AVPlayerViewController()
        vc.player = player
        vc.showsPlaybackControls = true
        vc.entersFullScreenWhenPlaybackBegins = false
        vc.videoGravity = .resizeAspect
        vc.view.clipsToBounds = true
        vc.view.backgroundColor = .black
        return vc
    }

    func updateUIViewController(_ uiViewController: AVPlayerViewController, context: Context) {
        uiViewController.view.clipsToBounds = true
        if uiViewController.player !== player {
            uiViewController.player = player
        }
    }
}

// MARK: - Smooth Hardware Telemetry Chart Card (VRAM / RAM / Disk)

struct SmoothTelemetryChartCard: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared

    private func smoothPath(points: [Double], in size: CGSize) -> Path {
        var path = Path()
        guard points.count >= 2 else { return path }
        let stepX = size.width / CGFloat(max(1, points.count - 1))
        let coords: [CGPoint] = points.enumerated().map { i, v in
            let clamped = min(1.0, max(0.0, v))
            return CGPoint(x: CGFloat(i) * stepX, y: size.height * (1.0 - CGFloat(clamped)))
        }
        path.move(to: coords[0])
        for i in 1..<coords.count {
            let prev = coords[i - 1]
            let cur = coords[i]
            let midX = (prev.x + cur.x) * 0.5
            path.addCurve(to: cur, control1: CGPoint(x: midX, y: prev.y), control2: CGPoint(x: midX, y: cur.y))
        }
        return path
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(L("实时云端硬件曲线", "Live Cloud Telemetry"), systemImage: "waveform.path.ecg")
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        vm.combinedTelemetryChartMode.toggle()
                    }
                } label: {
                    Text(vm.combinedTelemetryChartMode ? L("同屏叠加", "Overlay") : L("分项视图", "Split"))
                        .font(.caption.weight(.medium))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 4)
                        .background(Color.accentColor.opacity(0.14))
                        .foregroundColor(.accentColor)
                        .clipShape(Capsule())
                }
            }

            HStack(spacing: 10) {
                metricPill(
                    title: "VRAM",
                    value: vm.vramTotalGB > 0 ? String(format: "%.1f/%.0fG", vm.vramUsedGB, vm.vramTotalGB) : "--",
                    color: .orange
                )
                metricPill(
                    title: "RAM",
                    value: vm.ramTotalGB > 0 ? String(format: "%.1f/%.0fG", vm.ramUsedGB, vm.ramTotalGB) : "--",
                    color: .blue
                )
                metricPill(
                    title: "Disk",
                    value: vm.diskTotalGB > 0 ? String(format: "%.0f/%.0fG", vm.diskUsedGB, vm.diskTotalGB) : "--",
                    color: .green
                )
            }

            if vm.combinedTelemetryChartMode {
                GeometryReader { geo in
                    ZStack {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(Color(UIColor.tertiarySystemFill))
                        ForEach([0.25, 0.5, 0.75], id: \.self) { ratio in
                            Path { p in
                                let y = geo.size.height * CGFloat(ratio)
                                p.move(to: CGPoint(x: 0, y: y))
                                p.addLine(to: CGPoint(x: geo.size.width, y: y))
                            }
                            .stroke(Color.secondary.opacity(0.16), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                        }
                        let plotSize = CGSize(width: max(1, geo.size.width - 8), height: max(1, geo.size.height - 12))
                        if vm.vramHistoryPct.count >= 2 {
                            smoothPath(points: vm.vramHistoryPct, in: plotSize)
                                .stroke(Color.orange, lineWidth: 2.2)
                                .offset(x: 4, y: 6)
                        }
                        if vm.ramHistoryPct.count >= 2 {
                            smoothPath(points: vm.ramHistoryPct, in: plotSize)
                                .stroke(Color.blue, lineWidth: 1.9)
                                .offset(x: 4, y: 6)
                        }
                        if vm.diskHistoryPct.count >= 2 {
                            smoothPath(points: vm.diskHistoryPct, in: plotSize)
                                .stroke(Color.green, lineWidth: 1.7)
                                .offset(x: 4, y: 6)
                        }
                        if vm.vramHistoryPct.isEmpty {
                            Text(L("连接实例后实时绘制显存/内存/磁盘曲线", "Connect to plot live VRAM / RAM / Disk curves"))
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .frame(height: 92)
            } else {
                VStack(spacing: 8) {
                    singleMiniSparkline(label: "GPU VRAM", samples: vm.vramHistoryPct, color: .orange)
                    singleMiniSparkline(label: "System RAM", samples: vm.ramHistoryPct, color: .blue)
                    singleMiniSparkline(label: "NVMe Disk", samples: vm.diskHistoryPct, color: .green)
                }
            }
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private func metricPill(title: String, value: String, color: Color) -> some View {
        HStack(spacing: 5) {
            Circle().fill(color).frame(width: 7, height: 7)
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.caption2).foregroundColor(.secondary)
                Text(value).font(.caption.monospacedDigit().weight(.semibold)).lineLimit(1)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(color.opacity(0.09))
        .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
    }

    private func singleMiniSparkline(label: String, samples: [Double], color: Color) -> some View {
        HStack(spacing: 8) {
            Text(label)
                .font(.caption2.weight(.medium))
                .foregroundColor(.secondary)
                .frame(width: 72, alignment: .leading)
            GeometryReader { geo in
                ZStack {
                    RoundedRectangle(cornerRadius: 6).fill(Color(UIColor.tertiarySystemFill))
                    if samples.count >= 2 {
                        smoothPath(points: samples, in: geo.size)
                            .stroke(color, lineWidth: 2)
                    }
                }
            }
            .frame(height: 28)
            Text(samples.last.map { String(format: "%.0f%%", $0 * 100) } ?? "--")
                .font(.caption2.monospacedDigit().weight(.semibold))
                .frame(width: 36, alignment: .trailing)
        }
    }
}

// MARK: - Inline Media Preview Card (Video Player & HD Poster Preview)

struct MediaStageCard: View {
    @ObservedObject var vm: IOSStudioViewModel
    @State private var showReportConfirm: Bool = false

    var body: some View {
        if let mediaURL = vm.currentMediaURL {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label(
                        mediaURL.pathExtension.lowercased() == "mp4" ? L("最新生成视频预览", "Latest Video Output") : L("最新生成图像预览", "Latest Image Output"),
                        systemImage: mediaURL.pathExtension.lowercased() == "mp4" ? "play.rectangle.fill" : "photo.fill"
                    )
                    .font(.subheadline.weight(.semibold))
                    Spacer()
                    if let el = vm.mediaElapsedMap[mediaURL.lastPathComponent] {
                        Text(formatDuration(el, compact: true))
                            .font(.caption2.monospacedDigit().weight(.semibold))
                            .padding(.horizontal, 7)
                            .padding(.vertical, 3)
                            .background(Color.green.opacity(0.15))
                            .foregroundColor(.green)
                            .clipShape(Capsule())
                    }
                }

                if mediaURL.pathExtension.lowercased() == "mp4", let player = vm.player {
                    ClippedVideoPlayerView(player: player)
                        .frame(height: 240)
                        .clipped()
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                } else if let img = vm.currentPreviewImage {
                    Image(uiImage: img)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 320)
                        .frame(maxWidth: .infinity)
                        .background(Color.black.opacity(0.05))
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }

                HStack(spacing: 10) {
                    Button {
                        UIImpactFeedbackGenerator(style: .light).impactOccurred()
                        Task { await vm.saveMediaToSystemPhotos(url: mediaURL) }
                    } label: {
                        Label(L("存相册", "Save Photo"), systemImage: "square.and.arrow.down")
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 38)
                            .background(Color.accentColor.opacity(0.14))
                            .foregroundColor(.accentColor)
                            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)

                    Button {
                        UIImpactFeedbackGenerator(style: .light).impactOccurred()
                        vm.shareLocalMedia(mediaURL)
                    } label: {
                        Label(L("分享/导出", "Share"), systemImage: "square.and.arrow.up")
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 38)
                            .background(Color(UIColor.tertiarySystemFill))
                            .foregroundColor(.primary)
                            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)

                    Button {
                        UIImpactFeedbackGenerator(style: .light).impactOccurred()
                        showReportConfirm = true
                    } label: {
                        Image(systemName: "flag")
                            .font(.caption.weight(.semibold))
                            .frame(width: 40, height: 38)
                            .background(Color.red.opacity(0.11))
                            .foregroundColor(.red)
                            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(L("举报或清除异常内容", "Report or remove AI output"))
                }
            }
            .padding(14)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .confirmationDialog(
                L("AI 生成内容安全反馈", "AI Output Safety Action"),
                isPresented: $showReportConfirm,
                titleVisibility: .visible
            ) {
                Button(L("标记异常内容并从本机彻底删除", "Flag Inappropriate Output & Delete"), role: .destructive) {
                    vm.reportAndPurgeMedia(mediaURL)
                }
                Button(L("取消", "Cancel"), role: .cancel) {}
            } message: {
                Text(L("如模型生成了不符合预期或不当的内容，可立即将其标记并从本地作品库彻底移除。", "Immediately flag and permanently remove unexpected or inappropriate AI-generated media."))
            }
        }
    }
}

// MARK: - Gallery Tab View (MP4 Video & PNG Poster Library)

struct VideoThumbnailView: View {
    let url: URL
    @State private var thumbnail: UIImage? = nil

    var body: some View {
        ZStack {
            if let thumbnail {
                Image(uiImage: thumbnail)
                    .resizable()
                    .scaledToFill()
            } else {
                Color.black.opacity(0.8)
            }
            Image(systemName: "play.circle.fill")
                .font(.system(size: 32))
                .foregroundColor(.white.opacity(0.92))
                .shadow(radius: 4)
        }
        .task(id: url) {
            guard thumbnail == nil else { return }
            let asset = AVURLAsset(url: url)
            let gen = AVAssetImageGenerator(asset: asset)
            gen.appliesPreferredTrackTransform = true
            gen.maximumSize = CGSize(width: 420, height: 420)
            if let cg = try? gen.copyCGImage(at: .zero, actualTime: nil) {
                thumbnail = UIImage(cgImage: cg)
            }
        }
    }
}

struct GalleryTabView: View {
    @ObservedObject var vm: IOSStudioViewModel
    @ObservedObject var langMgr = LanguageManager.shared
    @State private var pendingDeleteItem: LocalMediaItem? = nil

    private let columns = [
        GridItem(.adaptive(minimum: 155), spacing: 12)
    ]

    private var activeItem: LocalMediaItem? {
        if let cur = vm.currentMediaURL,
           let matched = vm.localMediaItems.first(where: { $0.url.standardizedFileURL == cur.standardizedFileURL }) {
            return matched
        }
        return vm.localMediaItems.first
    }

    var body: some View {
        NavigationStack {
            Group {
                if vm.localMediaItems.isEmpty {
                    VStack(spacing: 14) {
                        Image(systemName: "photo.on.rectangle.angled")
                            .font(.system(size: 48))
                            .foregroundColor(.secondary)
                        Text(L("暂无本地生成的作品", "No Local Media Yet"))
                            .font(.headline)
                        Text(L("在「创作台」生成的所有高清视频与海报都会自动下载保存在此处，并可在系统的「文件」App -> EasyColab 中直接查看。", "Videos & posters generated in Create tab are saved here automatically and accessible in the iOS Files app."))
                            .font(.footnote)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 32)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ScrollView {
                        VStack(spacing: 14) {
                            if let active = activeItem {
                                activeViewerCard(active)
                            }

                            LazyVGrid(columns: columns, spacing: 12) {
                                ForEach(vm.localMediaItems) { item in
                                    galleryGridCell(item)
                                }
                            }
                        }
                        .padding(16)
                    }
                    .scrollDismissesKeyboard(.immediately)
                }
            }
            .background(Color(UIColor.systemGroupedBackground))
            .navigationTitle(L("作品库 (\(vm.localMediaItems.count))", "Gallery (\(vm.localMediaItems.count))"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        vm.refreshLocalMedia()
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
            .onAppear {
                syncActivePlayerIfNeeded()
            }
            .onChange(of: activeItem?.url) { _ in
                syncActivePlayerIfNeeded()
            }
            .confirmationDialog(
                L("确认删除该作品？", "Delete this media item?"),
                isPresented: Binding(
                    get: { pendingDeleteItem != nil },
                    set: { if !$0 { pendingDeleteItem = nil } }
                ),
                titleVisibility: .visible
            ) {
                if let target = pendingDeleteItem {
                    Button(L("从作品库删除 (\(target.filename))", "Delete \(target.filename)"), role: .destructive) {
                        vm.deleteLocalMedia(target)
                        pendingDeleteItem = nil
                    }
                }
                Button(L("取消", "Cancel"), role: .cancel) {
                    pendingDeleteItem = nil
                }
            } message: {
                Text(L("删除后将从 EasyColab 本地作品库中移除（已存入系统相册的副本不受影响）。", "Removes the file from EasyColab's local gallery (copies already saved to iOS Photos are unaffected)."))
            }
        }
    }

    private func syncActivePlayerIfNeeded() {
        guard let active = activeItem else { return }
        if vm.currentMediaURL?.standardizedFileURL != active.url.standardizedFileURL || (!active.isImage && vm.player == nil) {
            vm.selectMedia(active.url, autoPlay: false)
        }
    }

    private func activeViewerCard(_ item: LocalMediaItem) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            if item.isImage, let img = UIImage(contentsOfFile: item.url.path) {
                Image(uiImage: img)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 340)
                    .frame(maxWidth: .infinity)
                    .background(Color.black.opacity(0.05))
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            } else {
                ClippedVideoPlayerView(player: vm.player)
                    .frame(height: 250)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(item.filename)
                    .font(.caption.weight(.semibold))
                    .lineLimit(1)
                Text(String(format: "%.1f MB · %@", item.fileSizeMB, item.createdAt.formatted(date: .abbreviated, time: .shortened)))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            HStack(spacing: 10) {
                Button {
                    UIImpactFeedbackGenerator(style: .light).impactOccurred()
                    Task { await vm.saveMediaToSystemPhotos(url: item.url) }
                } label: {
                    Label(L("存相册", "Save"), systemImage: "square.and.arrow.down")
                        .font(.caption.weight(.semibold))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                        .frame(maxWidth: .infinity, minHeight: 40)
                        .background(Color.accentColor)
                        .foregroundColor(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                Button {
                    UIImpactFeedbackGenerator(style: .light).impactOccurred()
                    vm.shareLocalMedia(item.url)
                } label: {
                    Label(L("分享", "Share"), systemImage: "square.and.arrow.up")
                        .font(.caption.weight(.semibold))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                        .frame(maxWidth: .infinity, minHeight: 40)
                        .background(Color(UIColor.tertiarySystemFill))
                        .foregroundColor(.primary)
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                Button {
                    UIImpactFeedbackGenerator(style: .light).impactOccurred()
                    pendingDeleteItem = item
                } label: {
                    Label(L("删除", "Delete"), systemImage: "trash")
                        .font(.caption.weight(.semibold))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                        .frame(maxWidth: .infinity, minHeight: 40)
                        .background(Color.red.opacity(0.13))
                        .foregroundColor(.red)
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
        }
        .padding(12)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private func galleryGridCell(_ item: LocalMediaItem) -> some View {
        let isSelected = activeItem?.url.standardizedFileURL == item.url.standardizedFileURL
        return Button {
            vm.selectMedia(item.url, autoPlay: true)
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                ZStack(alignment: .bottomTrailing) {
                    Group {
                        if item.isImage, let img = UIImage(contentsOfFile: item.url.path) {
                            Image(uiImage: img)
                                .resizable()
                                .scaledToFill()
                        } else {
                            VideoThumbnailView(url: item.url)
                        }
                    }
                    .frame(height: 135)
                    .frame(maxWidth: .infinity)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

                    if let el = item.elapsedSeconds {
                        Text(formatDuration(el, compact: true))
                            .font(.caption2.monospacedDigit().weight(.bold))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(.ultraThinMaterial)
                            .clipShape(Capsule())
                            .padding(6)
                    }
                }
                Text(item.filename)
                    .font(.caption2.weight(.medium))
                    .foregroundColor(.primary)
                    .lineLimit(1)
            }
            .padding(8)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 2)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button {
                Task { await vm.saveMediaToSystemPhotos(url: item.url) }
            } label: {
                Label(L("存入系统相册", "Save to Photos"), systemImage: "square.and.arrow.down")
            }
            Button {
                vm.shareLocalMedia(item.url)
            } label: {
                Label(L("分享 / 导出", "Share / Export"), systemImage: "square.and.arrow.up")
            }
            Button(role: .destructive) {
                pendingDeleteItem = item
            } label: {
                Label(L("删除该作品", "Delete Media"), systemImage: "trash")
            }
        }
    }
}
